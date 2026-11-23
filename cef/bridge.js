// Installed only in the main document. The host independently checks its origin
// and execution context. This bridge exposes notifications, never filesystem APIs.
(() => {
  if (window !== window.top || !window.Notification || window.__centralNotificationAction) return;
  const Native = window.Notification;
  const notifications = new Map();
  let sequence = 0;
  const send = data => { if (typeof window.__centralNative === 'function') window.__centralNative(JSON.stringify(data)); };
  class CentralNotification extends EventTarget {
    static get permission() { return Native.permission; }
    static get maxActions() { return Native.maxActions || 0; }
    static requestPermission(callback) { return Native.requestPermission(callback); }
    constructor(title, options = {}) {
      super();
      if (Native.permission !== 'granted') throw new DOMException('Notification permission required', 'NotAllowedError');
      this.title = String(title); this.body = String(options.body || ''); this.tag = String(options.tag || '');
      this.icon = String(options.icon || ''); this.data = options.data; this.onclick = null; this.onclose = null; this.onshow = null;
      this._id = String(++sequence); notifications.set(this._id, this);
      send({kind:'notification',token:this._id,title:this.title.slice(0,512),body:this.body.slice(0,4096)});
      queueMicrotask(() => { const event = new Event('show'); this.dispatchEvent(event); this.onshow?.(event); });
    }
    close() {
      if (!notifications.delete(this._id)) return;
      send({kind:'notification-close',token:this._id});
      const event = new Event('close'); this.dispatchEvent(event); this.onclose?.(event);
    }
  }
  Object.defineProperty(window,'__centralNotificationAction',{value:(id,action)=>{
    const item=notifications.get(id); if(!item)return;
    if(action==='click'){ const event=new Event('click'); item.dispatchEvent(event); item.onclick?.(event); }
    else item.close();
  }});
  window.Notification = CentralNotification;
})();
