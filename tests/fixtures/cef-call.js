(async()=>{
 const result={userAgent:navigator.userAgent,codecs:RTCRtpSender.getCapabilities('video').codecs.map(c=>c.mimeType)};
 const streams=[],peers=[];
 try{
  const movie=document.createElement('video');movie.muted=true;movie.src='/sample.mp4';document.body.append(movie);
  await movie.play();await new Promise(r=>setTimeout(r,500));
  result.mp4={time:movie.currentTime,width:movie.videoWidth,error:movie.error?.code||null};movie.pause();
  const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:true});streams.push(stream);
  const videos=[0,1].map(()=>{const v=document.createElement('video');v.muted=true;v.autoplay=true;v.srcObject=new MediaStream();document.body.append(v);return v;});
  peers.push(new RTCPeerConnection({iceServers:[]}),new RTCPeerConnection({iceServers:[]}));
  const h264=RTCRtpSender.getCapabilities('video').codecs.filter(c=>c.mimeType==='video/H264');
  peers.forEach((peer,i)=>{
   peer.ontrack=e=>videos[i].srcObject.addTrack(e.track);
   stream.getTracks().forEach(track=>{
    const sender=peer.addTrack(track,stream);
    if(track.kind==='video')peer.getTransceivers().find(t=>t.sender===sender).setCodecPreferences(h264);
   });
  });
  const ice=p=>p.iceGatheringState==='complete'?Promise.resolve():new Promise((resolve,reject)=>{
   const t=setTimeout(()=>reject(Error('ice timeout')),6000);
   p.addEventListener('icegatheringstatechange',()=>{if(p.iceGatheringState==='complete'){clearTimeout(t);resolve();}});
  });
  await peers[0].setLocalDescription(await peers[0].createOffer());await ice(peers[0]);
  await peers[1].setRemoteDescription(peers[0].localDescription);
  await peers[1].setLocalDescription(await peers[1].createAnswer());await ice(peers[1]);
  await peers[0].setRemoteDescription(peers[1].localDescription);
  const deadline=Date.now()+10000;
  while(Date.now()<deadline && !peers.every(p=>p.connectionState==='connected'))await new Promise(r=>setTimeout(r,100));
  await new Promise(r=>setTimeout(r,1500));
  result.connections=peers.map(p=>p.connectionState);result.inbound=[];
  for(const p of peers){
   const stats=await p.getStats();
   result.inbound.push([...stats.values()].filter(s=>s.type==='inbound-rtp').map(s=>({
    kind:s.kind,packets:s.packetsReceived,frames:s.framesDecoded,
    codec:stats.get(s.codecId)?.mimeType
   })));
  }
 }catch(e){result.failure=e.name+': '+e.message;}
 finally{streams.forEach(s=>s.getTracks().forEach(t=>t.stop()));peers.forEach(p=>p.close());}
 return result;
})()
