// Central Chats CEF host. Local stdin/stdout IPC; no remote debugging port.
#include <atomic>
#include "json.hpp"
#include <fcntl.h>
#include <glib-unix.h>
#include <map>
#include <mutex>
#include <queue>
#include <iostream>
#include <fstream>
#include <sstream>
#include <cstring>
#include <unistd.h>
#include "include/cef_api_hash.h"
#include "include/capi/cef_app_capi.h"
#include "include/capi/cef_browser_capi.h"
#include "include/capi/cef_client_capi.h"
#include "include/capi/cef_display_handler_capi.h"
#include "include/capi/cef_frame_capi.h"
#include "include/capi/cef_life_span_handler_capi.h"
#include "include/capi/cef_load_handler_capi.h"
#include "include/capi/cef_permission_handler_capi.h"
#include "include/capi/cef_request_handler_capi.h"
#include "include/capi/cef_download_handler_capi.h"
#include "include/capi/cef_download_item_capi.h"
#include "include/capi/cef_dialog_handler_capi.h"
#include "include/capi/cef_devtools_message_observer_capi.h"
#include "include/capi/cef_parser_capi.h"
#include "include/capi/cef_task_capi.h"

template<class T> struct Ref {
 T object{}; std::atomic<int> count{1};
 Ref(){object.base.size=sizeof(T);
 object.base.add_ref=[](cef_base_ref_counted_t*b){reinterpret_cast<Ref*>(b)->count.fetch_add(1);};
 object.base.release=[](cef_base_ref_counted_t*b)->int{auto*r=reinterpret_cast<Ref*>(b);if(r->count.fetch_sub(1)==1){delete r;return 1;}return 0;};
 object.base.has_one_ref=[](cef_base_ref_counted_t*b)->int{return reinterpret_cast<Ref*>(b)->count.load()==1;};
 object.base.has_at_least_one_ref=[](cef_base_ref_counted_t*b)->int{return reinterpret_cast<Ref*>(b)->count.load()>0;};}
};
template<class T>T* hold(T*p){if(p)p->base.add_ref(&p->base);return p;}
template<class T>void drop(T*p){if(p)p->base.release(&p->base);}
static cef_string_t str(const std::string&s){cef_string_t r{};cef_string_utf8_to_utf16(s.data(),s.size(),&r);return r;}
static std::string utf(const cef_string_t*s){if(!s||!s->str)return "";cef_string_utf8_t r{};cef_string_utf16_to_utf8(s->str,s->length,&r);std::string v(r.str,r.length);cef_string_utf8_clear(&r);return v;}
static std::string take(cef_string_userfree_t s){auto v=utf(s);cef_string_userfree_free(s);return v;}
static std::string quote(const std::string&s){std::string out="\"";for(unsigned char c:s){if(c=='"'||c=='\\'){out+='\\';out+=c;}else if(c<32){char b[7];snprintf(b,7,"\\u%04x",c);out+=b;}else out+=c;}return out+'"';}
struct Json {
 nlohmann::json data;
 explicit Json(const std::string&s){data=nlohmann::json::parse(s,nullptr,false);}
 std::string s(const char*k){return data.is_object()&&data.contains(k)&&data[k].is_string()?data[k].get<std::string>():"";}
 int n(const char*k){return data.is_object()&&data.contains(k)&&data[k].is_number_integer()?data[k].get<int>():0;}
 bool b(const char*k){return data.is_object()&&data.contains(k)&&data[k].is_boolean()?data[k].get<bool>():false;}
 std::string value(const char*k){return data.is_object()&&data.contains(k)?data[k].dump():"null";}
};
static void emit(const std::string&s){std::cout<<s<<std::endl;}
static std::string origin(const std::string&url){auto u=str(url);cef_urlparts_t p{};p.size=sizeof(p);bool ok=cef_parse_url(&u,&p);cef_string_clear(&u);std::string result;
 if(ok && utf(&p.username).empty() && utf(&p.password).empty()) {auto scheme=utf(&p.scheme),host=utf(&p.host),port=utf(&p.port);if(scheme=="https"||scheme=="http")result=scheme+"://"+host+((port.empty()||(scheme=="https"&&port=="443")||(scheme=="http"&&port=="80"))?"":":"+port);}
 cef_string_clear(&p.spec);cef_string_clear(&p.scheme);cef_string_clear(&p.username);cef_string_clear(&p.password);cef_string_clear(&p.host);cef_string_clear(&p.port);cef_string_clear(&p.origin);cef_string_clear(&p.path);cef_string_clear(&p.query);cef_string_clear(&p.fragment);return result;}
static std::string url,allowed,bridge;static unsigned long parent_id;
static cef_browser_t* browser=nullptr;static cef_registration_t* registration=nullptr;
static std::string main_frame;static int seq=1000, context=0;static std::map<int,int> evaluations;
static std::map<int,cef_media_access_callback_t*> media;
static std::map<int,uint32_t> media_flags;
static std::map<int,cef_before_download_callback_t*> downloads;
static std::map<int,cef_permission_prompt_callback_t*> prompts;
static std::map<int,cef_file_dialog_callback_t*> file_dialogs;
static bool running=true;
static int dev(const std::string&method,const std::string&params="{}",int id=0){if(!browser)return 0;int identifier=id?id:++seq;auto*h=browser->get_host(browser);auto message="{\"id\":"+std::to_string(identifier)+",\"method\":"+quote(method)+",\"params\":"+params+"}";bool ok=h->send_dev_tools_message(h,message.data(),message.size());drop(h);return ok?identifier:0;}
static void eval(const std::string&script,int id=0,bool gesture=false){int n=++seq;if(id)evaluations[n]=id;dev("Runtime.evaluate","{\"expression\":"+quote(script)+",\"returnByValue\":true,\"awaitPromise\":true,\"userGesture\":"+std::string(gesture?"true":"false")+"}",n);}
static void external(const std::string&target){emit("{\"event\":\"external\",\"url\":"+quote(target)+"}");}
static void command(const std::string&line){Json j(line);auto action=j.s("action");
 if(action=="quit"){if(browser){auto*h=browser->get_host(browser);h->close_browser(h,true);drop(h);}else {running=false;cef_quit_message_loop();}}
 else if(!browser)return;
 else if(action=="reload")browser->reload(browser);
 else if(action=="load"){auto target=j.s("url");if(origin(target)==allowed){auto*f=browser->get_main_frame(browser);auto u=str(target);f->load_url(f,&u);cef_string_clear(&u);drop(f);}}
 else if(action=="eval")eval(j.s("script"),j.n("id"),j.b("gesture"));
 else if(action=="stop")browser->stop_load(browser);
 else if(action=="focus"){auto*h=browser->get_host(browser);h->set_focus(h,1);drop(h);}
 else if(action=="permission"){int id=j.n("id");bool allow=j.b("allow");if(media.count(id)){auto*c=media[id];if(allow)c->cont(c,media_flags[id]);else c->cancel(c);drop(c);media.erase(id);media_flags.erase(id);}else if(prompts.count(id)){auto*c=prompts[id];c->cont(c,allow?CEF_PERMISSION_RESULT_ACCEPT:CEF_PERMISSION_RESULT_DENY);drop(c);prompts.erase(id);}}
 else if(action=="files"){int id=j.n("id");if(file_dialogs.count(id)){auto*c=file_dialogs[id];auto list=cef_string_list_alloc();auto values=j.data.value("paths",nlohmann::json::array());if(values.is_array()){for(auto&v:values){if(v.is_string()){auto path=str(v.get<std::string>());cef_string_list_append(list,&path);cef_string_clear(&path);}}}if(cef_string_list_size(list))c->cont(c,list);else c->cancel(c);cef_string_list_free(list);drop(c);file_dialogs.erase(id);}}
 else if(action=="download"){int id=j.n("id");if(downloads.count(id)){auto*c=downloads[id];auto p=str(j.s("path"));if(p.length)c->cont(c,&p,0);cef_string_clear(&p);drop(c);downloads.erase(id);}}
 else if(action=="click"||action=="close-notification"){eval("window.__centralNotificationAction?.("+quote(j.s("token"))+","+quote(action)+")");}
}
int main(int argc,char**argv){
 std::string runtime,cache;for(int i=1;i<argc;i++){std::string a(argv[i]);if(a.rfind("--runtime=",0)==0)runtime=a.substr(10);if(a.rfind("--profile=",0)==0)cache=a.substr(10);if(a.rfind("--url=",0)==0)url=a.substr(6);if(a.rfind("--parent=",0)==0)parent_id=std::stoul(a.substr(9));}
 const char*hash=cef_api_hash(CEF_API_VERSION,0);if(!hash||strcmp(hash,CEF_API_HASH_PLATFORM))return 5;
 cef_main_args_t args{argc,argv};int sub=cef_execute_process(&args,nullptr,nullptr);if(sub>=0)return sub;
 allowed=origin(url);if(runtime.empty()||cache.empty()||allowed.empty()||!parent_id)return 2;
 std::ifstream in(runtime+"/bridge.js");std::stringstream buf;buf<<in.rdbuf();bridge=buf.str();if(bridge.empty())return 6;
 auto*app=&(new Ref<cef_app_t>())->object;auto*process=&(new Ref<cef_browser_process_handler_t>())->object;
 static cef_browser_process_handler_t*ph=process;app->get_browser_process_handler=[](cef_app_t*){return hold(ph);};
 auto*client=&(new Ref<cef_client_t>())->object;
 static auto*life=&(new Ref<cef_life_span_handler_t>())->object;
 static auto*load=&(new Ref<cef_load_handler_t>())->object;
 static auto*display=&(new Ref<cef_display_handler_t>())->object;
 static auto*permission=&(new Ref<cef_permission_handler_t>())->object;
 static auto*request=&(new Ref<cef_request_handler_t>())->object;
 static auto*download=&(new Ref<cef_download_handler_t>())->object;
 static auto*dialog=&(new Ref<cef_dialog_handler_t>())->object;
 static auto*observer=&(new Ref<cef_dev_tools_message_observer_t>())->object;
 client->get_life_span_handler=[](cef_client_t*){return hold(life);};client->get_load_handler=[](cef_client_t*){return hold(load);};client->get_display_handler=[](cef_client_t*){return hold(display);};client->get_permission_handler=[](cef_client_t*){return hold(permission);};client->get_request_handler=[](cef_client_t*){return hold(request);};client->get_download_handler=[](cef_client_t*){return hold(download);};client->get_dialog_handler=[](cef_client_t*){return hold(dialog);};
 observer->on_dev_tools_message=[](cef_dev_tools_message_observer_t*,cef_browser_t*,const void*,size_t)->int{return 0;};
 observer->on_dev_tools_agent_attached=[](cef_dev_tools_message_observer_t*,cef_browser_t*){};
 observer->on_dev_tools_agent_detached=[](cef_dev_tools_message_observer_t*,cef_browser_t*){};
 observer->on_dev_tools_method_result=[](cef_dev_tools_message_observer_t*,cef_browser_t*,int id,int success,const void*data,size_t size){if(id==1&&success&&browser)g_idle_add([](gpointer)->gboolean{if(browser){auto*f=browser->get_main_frame(browser);if(f){auto u=str(url);f->load_url(f,&u);cef_string_clear(&u);drop(f);}}return G_SOURCE_REMOVE;},nullptr);auto found=evaluations.find(id);if(found!=evaluations.end()){emit("{\"event\":\"result\",\"id\":"+std::to_string(found->second)+",\"success\":"+(success?"true":"false")+",\"data\":"+(size?std::string((const char*)data,size):"null")+"}");evaluations.erase(found);}};
 observer->on_dev_tools_event=[](cef_dev_tools_message_observer_t*,cef_browser_t*,const cef_string_t*m,const void*data,size_t size){std::string method=utf(m);Json j(std::string((const char*)data,size));
 if(method=="Page.frameNavigated"){Json f(j.value("frame"));if(f.s("parentId").empty())main_frame=f.s("id");}
 else if(method=="Runtime.executionContextCreated"){Json c(j.value("context"));Json aux(c.value("auxData"));if(aux.b("isDefault")&&aux.s("frameId")==main_frame&&c.s("origin")==allowed){context=c.n("id");}}
 else if(method=="Runtime.executionContextsCleared")context=0;
 else if(method=="Runtime.bindingCalled"&&j.s("name")=="__centralNative"&&context&&j.n("executionContextId")==context){Json payload(j.s("payload"));auto kind=payload.s("kind");if(kind=="notification"||kind=="notification-close"||kind=="notification-permission")emit("{\"event\":\"bridge\",\"data\":"+j.s("payload")+"}");}
 };
 life->on_after_created=[](cef_life_span_handler_t*,cef_browser_t*b){browser=hold(b);auto*h=b->get_host(b);emit("{\"event\":\"window\",\"id\":"+std::to_string(h->get_window_handle(h))+"}");registration=h->add_dev_tools_message_observer(h,observer);drop(h);dev("Runtime.enable");dev("Page.enable");dev("Runtime.addBinding","{\"name\":\"__centralNative\"}");dev("Page.addScriptToEvaluateOnNewDocument","{\"source\":"+quote(bridge)+"}",1);};
 life->on_before_popup=[](cef_life_span_handler_t*,cef_browser_t*,cef_frame_t*,int,const cef_string_t*target,const cef_string_t*,cef_window_open_disposition_t,int gesture,const cef_popup_features_t*,cef_window_info_t*,cef_client_t**,cef_browser_settings_t*,cef_dictionary_value_t**,int*)->int{if(gesture)external(utf(target));return 1;};
 life->on_before_close=[](cef_life_span_handler_t*,cef_browser_t*){for(auto&[id,c]:media){c->cancel(c);drop(c);}media.clear();for(auto&[id,c]:prompts){c->cont(c,CEF_PERMISSION_RESULT_DENY);drop(c);}prompts.clear();for(auto&[id,c]:downloads)drop(c);downloads.clear();for(auto&[id,c]:file_dialogs){c->cancel(c);drop(c);}file_dialogs.clear();drop(registration);registration=nullptr;drop(browser);browser=nullptr;running=false;cef_quit_message_loop();};
 request->on_before_browse=[](cef_request_handler_t*,cef_browser_t*,cef_frame_t*f,cef_request_t*r,int gesture,int)->int{if(!f->is_main(f))return 0;auto target=take(r->get_url(r));if(target=="about:blank"||origin(target)==allowed)return 0;if(gesture)external(target);return 1;};
 load->on_load_start=[](cef_load_handler_t*,cef_browser_t*,cef_frame_t*f,cef_transition_type_t){if(f->is_main(f))emit("{\"event\":\"loading\"}");};
 load->on_load_end=[](cef_load_handler_t*,cef_browser_t*,cef_frame_t*f,int status){if(f->is_main(f)&&origin(take(f->get_url(f)))==allowed)emit("{\"event\":\"loaded\",\"ok\":"+std::string(status<400?"true":"false")+"}");};
 load->on_load_error=[](cef_load_handler_t*,cef_browser_t*,cef_frame_t*f,cef_errorcode_t code,const cef_string_t*,const cef_string_t*){if(f->is_main(f)&&code!=ERR_ABORTED)emit("{\"event\":\"loaded\",\"ok\":false}");};
 display->on_address_change=[](cef_display_handler_t*,cef_browser_t*,cef_frame_t*f,const cef_string_t*u){if(f->is_main(f))emit("{\"event\":\"url\",\"url\":"+quote(utf(u))+"}");};
 display->on_fullscreen_mode_change=[](cef_display_handler_t*,cef_browser_t*,int on){emit("{\"event\":\"fullscreen\",\"on\":"+std::string(on?"true":"false")+"}");};
 display->on_console_message=[](cef_display_handler_t*,cef_browser_t*,cef_log_severity_t,const cef_string_t*,const cef_string_t*,int)->int{return 1;};
 permission->on_request_media_access_permission=[](cef_permission_handler_t*,cef_browser_t*,cef_frame_t*,const cef_string_t*u,uint32_t flags,cef_media_access_callback_t*c)->int{if(origin(utf(u))!=allowed||!flags||(flags&~3)){c->cancel(c);return 1;}int id=++seq;media[id]=hold(c);media_flags[id]=flags;emit("{\"event\":\"permission\",\"id\":"+std::to_string(id)+",\"flags\":"+std::to_string(flags)+",\"origin\":"+quote(allowed)+"}");return 1;};
 permission->on_show_permission_prompt=[](cef_permission_handler_t*,cef_browser_t*,uint64_t,const cef_string_t*u,uint32_t flags,cef_permission_prompt_callback_t*c)->int{if(origin(utf(u))!=allowed||flags!=CEF_PERMISSION_TYPE_NOTIFICATIONS){c->cont(c,CEF_PERMISSION_RESULT_DENY);return 1;}int id=++seq;prompts[id]=hold(c);emit("{\"event\":\"permission\",\"id\":"+std::to_string(id)+",\"flags\":0,\"origin\":"+quote(allowed)+"}");return 1;};
 download->can_download=[](cef_download_handler_t*,cef_browser_t*,const cef_string_t*,const cef_string_t*)->int{return 1;};
 download->on_before_download=[](cef_download_handler_t*,cef_browser_t*,cef_download_item_t*i,const cef_string_t*name,cef_before_download_callback_t*c)->int{int id=i->get_id(i);downloads[id]=hold(c);emit("{\"event\":\"download\",\"id\":"+std::to_string(id)+",\"name\":"+quote(utf(name))+"}");return 1;};
 download->on_download_updated=[](cef_download_handler_t*,cef_browser_t*,cef_download_item_t*i,cef_download_item_callback_t*){if(i->is_complete(i)||i->is_interrupted(i)||i->is_canceled(i))emit("{\"event\":\"download-state\",\"id\":"+std::to_string(i->get_id(i))+",\"complete\":"+std::string(i->is_complete(i)?"true":"false")+",\"path\":"+quote(take(i->get_full_path(i)))+"}");};
 dialog->on_file_dialog=[](cef_dialog_handler_t*,cef_browser_t*,cef_file_dialog_mode_t mode,const cef_string_t*,const cef_string_t*,cef_string_list_t,cef_string_list_t,cef_string_list_t,cef_file_dialog_callback_t*c)->int{int id=++seq;file_dialogs[id]=hold(c);emit("{\"event\":\"file-dialog\",\"id\":"+std::to_string(id)+",\"mode\":"+std::to_string(mode)+"}");return 1;};
 static cef_client_t*cl=client;
 process->on_context_initialized=[](cef_browser_process_handler_t*){cef_window_info_t info{};info.size=sizeof(info);info.parent_window=parent_id;info.bounds={0,0,1000,600};info.runtime_style=CEF_RUNTIME_STYLE_ALLOY;cef_browser_settings_t settings{};settings.size=sizeof(settings);auto blank=str("about:blank");if(!cef_browser_host_create_browser(&info,cl,&blank,&settings,nullptr,nullptr)){running=false;cef_quit_message_loop();}cef_string_clear(&blank);};
 cef_settings_t settings{};settings.size=sizeof(settings);settings.root_cache_path=str(cache);settings.cache_path=str(cache+"/profile");settings.resources_dir_path=str(runtime);settings.locales_dir_path=str(runtime+"/locales");settings.log_severity=LOGSEVERITY_DISABLE;settings.persist_session_cookies=1;
 if(!cef_initialize(&args,&settings,app,nullptr))return 3;
 // Use CEF's native GLib event loop. Its X11 sources must process actual
 // pointer, keyboard and ConfigureNotify events, not only Chromium tasks.
 fcntl(STDIN_FILENO,F_SETFL,fcntl(STDIN_FILENO,F_GETFL)|O_NONBLOCK);
 static std::string input;
 auto watch=g_unix_fd_add(STDIN_FILENO,GIOCondition(G_IO_IN|G_IO_HUP|G_IO_ERR),[](gint fd,GIOCondition,gpointer)->gboolean{
  char buffer[8192];auto count=read(fd,buffer,sizeof(buffer));
  if(count==0){command("{\"action\":\"quit\"}");return G_SOURCE_REMOVE;}
  if(count>0){input.append(buffer,count);if(input.size()>8*1024*1024){command("{\"action\":\"quit\"}");input.clear();return G_SOURCE_REMOVE;}size_t end;while((end=input.find('\n'))!=std::string::npos){auto line=input.substr(0,end);input.erase(0,end+1);command(line);}}
  return G_SOURCE_CONTINUE;
 },nullptr);
 cef_run_message_loop();
 if(g_main_context_find_source_by_id(nullptr,watch))g_source_remove(watch);
 cef_shutdown();return 0;
}
