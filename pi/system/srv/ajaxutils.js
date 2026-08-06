/*******************************************************
* Copyright (C) 2020 onwards
* Evodyne Robotics Corporation / Evodyne Robotics Academy
* support@evodyneacademy.com
* Can not be copied and/or distributed under any
* circumstances, directly or
* indirectly, verbatim or modified or derived or inspired
*******************************************************/

function did(id){return document.getElementById(id);}
function hide(n){did(n).style.display="none";}
function show(n){did(n).style.display="";}
function tog(n){var o=did(n);o.style.display=(o.style.display==""?"none":"");}
function sho(n,s){s?show(n):hide(n);}
function hasProp(o,p){return o.hasOwnProperty(p);}
function isempty(o) { return (Object.keys(o).length == 0) };
String.prototype.capitalize = function(){
  return this.replace( /(^|\s)([a-z])/g , function(m,p1,p2){ return p1+p2.toUpperCase(); } );
};
function showWaitCursor( show, pos )
{
  var o=did((!pos || pos == 0) ? "waitcursor" : "waitcursor1" );
  if (o) o.innerHTML=(show ? "<img src='/images/wait20.gif'>" : "" );
}
var showError = function ( line )
{
  //if(did("errorinfo")) did("errorinfo").innerHTML = line;
  if(line&&line!="")
    alert(line);
}
function getClientWidth(){
	return document.compatMode=='CSS1Compat' && !window.opera?document.documentElement.clientWidth:document.body.clientWidth;
}
function getClientHeight(){
	return document.compatMode=='CSS1Compat' && !window.opera?document.documentElement.clientHeight:document.body.clientHeight;
}
function findPos(obj)
{
  var cl=0;//left
  var ct=0;//top
  if(obj.offsetParent)
  {
    while(obj.offsetParent)
    {
      cl+=obj.offsetLeft-obj.scrollLeft;
      ct+=obj.offsetTop-obj.scrollTop;
      var position='';
      if(obj.style&&obj.style.position) position=obj.style.position.toLowerCase();
      if ((position=='absolute')||(position=='relative')) break;
      while(obj.parentNode!=obj.offsetParent) {
        obj=obj.parentNode;
        cl-=obj.scrollLeft;
        ct-=obj.scrollTop;
      }
      obj=obj.offsetParent;
    }
  }
  else{
    if(obj.x)
			cl+=obj.x;
    if (obj.y)
			ct+=obj.y;
  }
  return {left:cl,top:ct};
}
function setPos(o,pos)
{
  var l=pos.left;
  var t=pos.top;
  var r=l+o.offsetWidth;
  var b=t+o.offsetHeight;
  var w=getClientWidth();
  var h=document.body.scrollTop+getClientHeight();
  if(r>w)
    l-=(r-w);
  if(b>h)
    t-=(b-h);
  o.style.left=l+"px";
  o.style.top=t+"px";
}

function encu(str){return encodeURIComponent( str );}
function cb(n){return (did(n).checked?"1":"0");}


function execAjaxPost( url, params, callback_fn, waitcursorpos )
{
  var formdata = new FormData();
  for(var key in params)
  {
    if(params.hasOwnProperty(key))
    {
      formdata.append( key, params["key"] );
    }
  }
  var xmlhttp = null;
  if ( xmlhttp == null )
  {
    if (window.XMLHttpRequest)
    {// code for IE7, Firefox, Mozilla, etc.
      xmlhttp =new XMLHttpRequest();
    }
    else if (window.ActiveXObject)
    {// code for IE5, IE6
      xmlhttp	 = new ActiveXObject("Microsoft.XMLHTTP");
    }
  }
  else
  {
    xmlhttp.abort();
  }
  if (xmlhttp != null && ( xmlhttp.readyState == 4 || xmlhttp.readyState == 0 ) )
  {
    xmlhttp.onreadystatechange = 
    function() { 
      if( this.readyState==4 ) 
      { 
        showWaitCursor( false, waitcursorpos );
        if ( this.status==200 )
          callback_fn( this.responseText ); 
		
        this.obj = null; 
      } 
    };
    showWaitCursor( true, waitcursorpos );
    xmlhttp.open("POST",url,true);
    xmlhttp.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    xmlhttp.send(formdata);
  }
  else
  {
    // post("Your browser does not support XMLHTTP.");
  }
}

function execAjax( url, callback_fn, waitcursorpos )
{
  var xmlhttp = null;
  if ( xmlhttp == null )
  {
    if (window.XMLHttpRequest)
    {// code for IE7, Firefox, Mozilla, etc.
      xmlhttp =new XMLHttpRequest();
    }
    else if (window.ActiveXObject)
    {// code for IE5, IE6
      xmlhttp	 = new ActiveXObject("Microsoft.XMLHTTP");
    }
  }
  else
  {
    xmlhttp.abort();
  }
  if (xmlhttp != null && ( xmlhttp.readyState == 4 || xmlhttp.readyState == 0 ) )
  {
    xmlhttp.onreadystatechange = 
    function() { 
      if( this.readyState==4 ) 
      { 
        showWaitCursor( false, waitcursorpos );
        if ( this.status==200 )
          callback_fn( this.responseText ); 
		
        this.obj = null; 
      } 
    };
    showWaitCursor( true, waitcursorpos );
    xmlhttp.open("GET",url,true);
    xmlhttp.send(null);
  }
  else
  {
    // post("Your browser does not support XMLHTTP.");
  }
}

function execAjaxQuery( script, params, callbackfn, noauth,waitcursorpos )
{
  if (noauth)
    noauth=true;
  var url=script;
  if (noauth )
  {
    if (params && params != "" )
      url += "?" + params;
  }
  else
  {
    url += "?" + "u=" + username + "&t=" + token;
    if ( params && params != "" )
      url += "&" + params;
  }
  //document.getElementById("debuginfo").innerHTML = url;
  if (!waitcursorpos) waitcursorpos=0;
  //did('debuginfo').innerHTML=url;
  execAjax( url, onFetchedResponse,waitcursorpos );
  //showError( "" );
  function onFetchedResponse(responseText)
  {
    var response = eval( '(' + responseText + ')' );
    if ( response.errcode == 0 )
    {
      callbackfn( response );
    }
    else if ( response.errcode == 120 )
    {
      if ( typeof signOut == 'function')
        signOut();
      else
        showError("You are not signed in");
    }
    else
      showError( response.errmsg );
    this.obj = null;
  }
}

function cloneObject(what){
  var o={};
  for (i in what){
    if (typeof what[i] == 'object') {
      o[i] = cloneObject(what[i]);
    }
    else
      o[i] = what[i];
  }
  return o;
}
function joinObject(o,dp,dv)
{
  var a=[];
  for(n in o)
  {
    a.push( n+dv+o[n]);
  }
  return a.join(dp);
}


function execAjaxSimplePost( url, params, callback_fn, neterrorfn )
{
  var pdata = "";
  var sep = "";
  for(var key in params)
  {
    if(params.hasOwnProperty(key))
    {
      pdata += sep + key + "=" + encodeURIComponent(params[key]);
      sep = "&";
    }
  }
  var xmlhttp = null;
  if ( xmlhttp == null )
  {
    if (window.XMLHttpRequest)
    {// code for IE7, Firefox, Mozilla, etc.
      xmlhttp =new XMLHttpRequest();
    }
    else if (window.ActiveXObject)
    {// code for IE5, IE6
      xmlhttp	 = new ActiveXObject("Microsoft.XMLHTTP");
    }
  }
  else
  {
    xmlhttp.abort();
  }
  if (xmlhttp != null && ( xmlhttp.readyState == 4 || xmlhttp.readyState == 0 ) )
  {
    xmlhttp.onreadystatechange = 
    function() { 
      if( this.readyState==4 ) 
      { 
        if ( this.status==200 )
            callback_fn( this.responseText );
        else
            neterrorfn();
		
        this.obj = null; 
      } 
    };
    xmlhttp.open("POST",url,true);
    //xmlhttp.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
    xmlhttp.send(pdata);
  }
  else
  {
      // post("Your browser does not support XMLHTTP.");
      neterrorfn();
  }
}

function execAjaxSimple( url, callback_fn, neterrorfn )
{
  var xmlhttp = null;
  if ( xmlhttp == null )
  {
    if (window.XMLHttpRequest)
    {// code for IE7, Firefox, Mozilla, etc.
      xmlhttp =new XMLHttpRequest();
    }
    else if (window.ActiveXObject)
    {// code for IE5, IE6
      xmlhttp	 = new ActiveXObject("Microsoft.XMLHTTP");
    }
  }
  else
  {
    xmlhttp.abort();
  }
  if (xmlhttp != null && ( xmlhttp.readyState == 4 || xmlhttp.readyState == 0 ) )
  {
    xmlhttp.onreadystatechange = 
    function() { 
      if( this.readyState==4 ) 
      { 
        if ( this.status==200 )
            callback_fn( this.responseText );
        else
            neterrorfn();
		
        this.obj = null; 
      } 
    };
    xmlhttp.open("GET",url,true);
    xmlhttp.send(null);
  }
  else
  {
      // post("Your browser does not support XMLHTTP.");
      neterrorfn();
  }
}

function execAjaxSimpleJson( script, params, callbackfn, neterrorfn )
{
  var url=script;
  if (params && params != "" )
      url += "?" + params;

  execAjaxSimple( url, onFetchedResponse, neterrorfn );
  function onFetchedResponse(responseText)
  {
     var response = eval( '(' + responseText + ')' );
      callbackfn( response );
      this.obj = null;
  }
}
function sortNumber(a, b){return a - b;}
function pad(num, size){ return ('000000000' + num).substr(-size); }
function $(str) {
    return document.getElementById(str);
}
