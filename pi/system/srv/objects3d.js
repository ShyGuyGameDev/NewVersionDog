var renderer = null;
var mesh = null;
var scene = null;
var camera = null;
var controls = null;
var axis_color = 0x0000ff; //blue
var white_color = 0xffffff;
var inch2meters = 0.0254; //in meters
var inch2mm = 25.4; //in mm
var oneinch = 25.4;
var onemeter = 1000;
var d2r = Math.PI/180.0;
var r2d = 180.0/Math.PI;
var deg180 = 180.0 * d2r;
var deg90 = 90.0 * d2r;
var deg45 = 45.0 * d2r;
var axis_material = new THREE.MeshBasicMaterial ( {color: axis_color} );

var materials={}; //keep dict by color

var line_materials={};
line_materials["black"] = new THREE.LineBasicMaterial( { color: 0x000000 } );
line_materials["red"] = new THREE.LineBasicMaterial( { color: 0xff0000 } );
line_materials["green"] = new THREE.LineBasicMaterial( { color: 0x00ff00 } );
line_materials["blue"] = new THREE.LineBasicMaterial( { color: 0x0000ff } );

var black_line_material = new THREE.LineBasicMaterial( { color: 0x000000 } );
var red_line_material = new THREE.LineBasicMaterial( { color: 0xff0000 } );
var green_line_material = new THREE.LineBasicMaterial( { color: 0x00ff00 } );
var blue_line_material = new THREE.LineBasicMaterial( { color: 0x0000ff } );

var yellow_line_material = new THREE.LineBasicMaterial( { color: 0xffff00 } );



var robot_height = 0;
var default_camera_pos = [-onemeter,-onemeter,1.5*onemeter];
var world = null;
var glocation = "";
var mapinfo = {"height":2000, "width":2000,"xoffset":1000,"yoffset":1000, "ts":{"s":0,"ns":0}};

var allobjects = {};
var meshObjs = [];

function getMaterial(color)
{
    if(materials.hasOwnProperty(color))
    {
        return materials[color];
    }
    materials[color]= new THREE.MeshPhongMaterial ( {color: color, shininess:100, specular:0x111111} );
    return materials[color];
}
function getMaterialAlpha(color, opacity)
{
    var col = color;
    var transp = false;
    if ( opacity && opacity != "1.0" && opacity != 1 && opacity != "1" )
    {
        col = col + "-" + opacity;
        console.log( "Color is ",  col );
        transp = true;
    }
    
    if(materials.hasOwnProperty(col))
    {
        return materials[col];
    }
    materials[col]= new THREE.MeshPhongMaterial ( {color: color,
                                                   shininess:100,
                                                   specular:0x111111,
                                                   opacity: opacity,
                                                   transparent: transp
                                                  } );
    return materials[col];
}

var texture_materials = {};
function getTextureMaterial(name)
{
    if(textures_materials.hasOwnProperty(name))
    {
        return textures_materials[name];
    }
    console.log( "Loading " + name );
    var texture = new THREE.TextureLoader().load( name );
    texture_materials[name]= new THREE.MeshBasicMaterial ( {map:texture} );
    return texture_materials[name];
}
function removeTextureMaterial(name)
{
    if(texture_materials.hasOwnProperty(name))
    {
        var t = texture_materials[name];
        delete texture_materials[name];
        disposeNode(t);
        t=null;
    }    
}
var textures = {};
function getTexture(name,material)
{
    if(textures.hasOwnProperty(name))
    {
        return textures[name];
    }
    console.log( "Loading texture " + name );
    if (material) //passed
    {   //use onload
        textures[name] = new THREE.TextureLoader().load( name,
                                                         function(tex){
                                                             material.map = tex;
                                                         });
    }
    else
    {
        textures[name] = new THREE.TextureLoader().load( name );
    }
    return textures[name];
}
function removeTexture(name)
{
    if(textures.hasOwnProperty(name))
    {
        var t = textures[name];
        delete textures[name];
        disposeNode(t);
        t=null;
    }
}

function getTextMesh(txt,color,sz,flat)
{
    /////// draw text on canvas /////////
    var canvas = document.createElement('canvas');
    if (!sz)
        sz = "40";
    canvas.width = txt.length * parseInt(sz) +50;
    var context = canvas.getContext('2d');
    context.font = "Bold "+sz+"px Arial";
    if (!color) color = "red";
    context.fillStyle = color;//"rgba(255,0,0,0.95)";
    //var w = context.measureText(txt).width;
    //console.log( "w: " + w + " c: " + canvas.height );
    context.fillText(txt, 0, parseInt(sz)+10);

    // canvas contents will be used for a texture
    var texture = new THREE.Texture(canvas)
    texture.needsUpdate = true;

    var material = new THREE.MeshBasicMaterial( {map: texture, side:THREE.DoubleSide } );
    material.transparent = true;

    var mesh = new THREE.Mesh(
        new THREE.PlaneBufferGeometry(canvas.width, canvas.height),
        material
    );
    mesh.position.set(canvas.width/2,0,-(parseInt(sz)/2));
    if (!flat)
        mesh.rotation.set(deg90,0,0);
    return mesh;
}

function getProp(obj,prop,def)
{
    //return default value if doesnt exist
    if(obj.hasOwnProperty(prop))
        return obj[prop];
    return def;
}


//stuff for initializing visualization
function pageinit()
{
    var div = document.getElementById('three');
    var width = div.offsetWidth;
    var height = div.offsetHeight;
    renderer = new THREE.WebGLRenderer({ antialias: true } );
    renderer.setPixelRatio( window.devicePixelRatio );
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap; // default THREE.PCFShadowMap
    div.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    scene.background = new THREE.Color( 0xaaaaaa );

    var light = new THREE.HemisphereLight( 0xffffff, 0xeeeeee, 0.5 );
    scene.add( light );
    
    camera = new THREE.PerspectiveCamera(70, width / height, 0.1*onemeter, 25*onemeter);
    camera.position.set( -onemeter/3,-onemeter/3,1.5*onemeter/3 );
    camera.up.set(0,0,1);

    scene.add( camera );

    controls = new THREE.OrbitControls( camera, renderer.domElement);
    controls.update();

    createEnv();

    animate();

/*
    // enable clickable 3D objects
    var raycaster = new THREE.Raycaster();
    var mouse = new THREE.Vector2();
 
    // See https://stackoverflow.com/questions/12800150/catch-the-click-event-on-a-specific-mesh-in-the-renderer
    // Handle all clicks to determine of a three.js object was clicked and trigger its callback
    function onDocumentMouseDown(event) 
    {
        event.preventDefault();
        mouse.x = (event.clientX / renderer.domElement.clientWidth) * 2 - 1;
        mouse.y =  - (event.clientY / renderer.domElement.clientHeight) * 2 + 1;
 
        raycaster.setFromCamera(mouse, camera);
         
        var intersects = raycaster.intersectObjects(meshObjs);
 
        //if (intersects.length &amp;amp;gt; 0) 
        for( var i = 0; i < intersects.length; i++)
        {
            intersects[i].object.callback();
            //intersects[0].object.callback();
        }
    }

    document.addEventListener('mousedown', onDocumentMouseDown, false);
*/
}

function animate()
{
    requestAnimationFrame(animate);
    controls.update(); //added
    renderer.render(scene, camera);
}

function togsize(a)
{
    var o=did("three");
    var h=0;
    var w=0;
    if (o.offsetWidth>500)
    {
        w=420;
        h=320;
    }
    else
    {
        w=window.innerWidth - 20;
        if ( a && a == 1 )
            h = 400;
        else
            h=window.innerHeight - 20;
    }
    o.style.width = w+"px";
    o.style.height = h+"px";

    var width = o.offsetWidth;
    var height = o.offsetHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    
    //alert( w +","+h );
}

function disposeNode (node)
{
    if(node)
    {
        if (node.geometry)
        {
            node.geometry.dispose();
            node.geometry = null; // fixed problem
        }

        if (node.material)
        {
            if (node.material instanceof THREE.MeshFaceMaterial)
            {
                $.each (node.material.materials, function (idx, mtrl)
                {
                    if (mtrl.map)           mtrl.map.dispose ();
                    if (mtrl.lightMap)      mtrl.lightMap.dispose ();
                    if (mtrl.bumpMap)       mtrl.bumpMap.dispose ();
                    if (mtrl.normalMap)     mtrl.normalMap.dispose ();
                    if (mtrl.specularMap)   mtrl.specularMap.dispose ();
                    if (mtrl.envMap)        mtrl.envMap.dispose ();

                    mtrl.dispose ();    // disposes any programs associated with the material
                    mtrl.deallocate();
                    mrtl = null; // fixed problem
                });
            }
            else
            {
                if (node.material.map)          node.material.map.dispose ();
                if (node.material.lightMap)     node.material.lightMap.dispose ();
                if (node.material.bumpMap)      node.material.bumpMap.dispose ();
                if (node.material.normalMap)    node.material.normalMap.dispose ();
                if (node.material.specularMap)  node.material.specularMap.dispose ();
                if (node.material.envMap)       node.material.envMap.dispose ();

                node.material.dispose ();   // disposes any programs associated with the material
                node.material = null; // fixed problem
            }
        }
        node = null;
    }
}   // disposeNode


function removepcd(id)
{
    if(allobjects[id].hasOwnProperty("pcd") && allobjects[id].pcd )
    {
        console.log( "removing pcd for " + id );
        //allobjects[id].obj_origin.remove(allobjects[id].pcd);
        scene.remove(allobjects[id].pcd); //we have been adding to scene instead of obj
        disposeNode(allobjects[id].pcd);
        allobjects[id].pcd = null;
        allobjects[id].obj_origin.ts = null;
        //delete allobjects[id].pcd;
    }
}
function removeObject(id)
{
    console.log( "removing object " + id );
    if (!hasProp(allobjects,id))
        return;
    removepcd(id); //if any
    var o = allobjects[id];
    if (o.parent_id == "WORLD")
        scene.remove(o.obj_origin);
    else if (o.obj_origin)
        o.obj_origin.parent.remove(o.obj_origin);
    delete allobjects[id];
    disposeNode(o);
}

// Default click handler for our three.js objects
function objectClickHandler() {
    console.log("Opening Google\n");
    window.open('http://www.google.com/', '_blank');
}

var pointsMaterial = new THREE.PointsMaterial({size: 20, vertexColors: THREE.VertexColors});
var color = pointsMaterial.color.clone();
pointsMaterial.color.setRGB(color.b, color.g, color.r);

var octoPtsMaterial = new THREE.PointsMaterial({size: 80, vertexColors: THREE.VertexColors});

function arrayRemove(arr, value) {
   return arr.filter(function(ele){
       return ele != value;
   });
}

var surface_id_prefix = "SURFACE-";
var surface_id_prefix_len = surface_id_prefix.length;
var hidden_surfaces = {};
function hideSurface(id)
{
    id=id+"";
    hidden_surfaces[id]=true;
    removeObject( surface_id_prefix+id );
    if (did("sid-"+id) )
        did("sid-"+id).style.color="red";
    console.log( hidden_surfaces );
}
function unhideSurface(id)
{
    hidden_surfaces[id] = false;
    delete hidden_surfaces[id];
    if (did("sid-"+id) )
        did("sid-"+id).style.color="";
}
function hideAllSurfaces()
{
    for(i=0;i<g_surface_ids.length;i++)
    {
        var id=g_surface_ids[i].substring(surface_id_prefix_len);
        hideSurface(id);
    }
}
function isSurfaceHidden(id)
{
    id=id+"";
    return hidden_surfaces.hasOwnProperty(id) && hidden_surfaces[id];
}

var min_pcd_update_interval = 1; //seconds
function loadPCD(obj,o,parent_obj)
{
    var pcd = getPCD(o);
    var type = getPCDType(o);
    var timestamp = (hasProp(o,"ts") ? parseInt(o["ts"]):0);
    
    if ( pcd )
    {
        var id = pcd;
        if ( type == "surface" && isSurfaceHidden(id) )
            return;
        var existing_timestamp = (hasProp(obj,"ts")? obj.ts : 0 );
        if ( (existing_timestamp + min_pcd_update_interval) >= timestamp )
        {
            //console.log( "not replacing pcd since latest exists " + pcd  +
            //",old=" + existing_timestamp + " new=" + timestamp );
            return;
        }
    }
    if (pcd ) 
    {
        var loader = new PCDLoader();
        console.log( "loading pcd for " + type + " " + pcd );
        loader.load(
            "getpcd?id="+pcd+"&type="+type,
            function(mesh) 
            {
                // set size of point and get color from pcd file
                // pass point settings into the mesh
                mesh.material = pointsMaterial;
                //points are in world frame
                //lets try adding to scene instead of calculated centroid object of surface
                mesh.callback = objectClickHandler;
                //console.log( "adding mesh " +pcd + ", type=" + type);
                //obj.add(mesh);
                scene.add(mesh);

                //remove previous if exists
                if (parent_obj.hasOwnProperty("pcd"))
                {
                    var pmesh = parent_obj.pcd;
                    parent_obj.pcd = null;
                    scene.remove(pmesh);
                    obj["ts"] = null;
                    disposeNode(pmesh);
                    pmesh = null;
                }
                parent_obj["pcd"] = mesh; //remember in parent_obj
                obj["ts"] = timestamp;

                controls.update();
            },
            function(xhr) 
            {
                //console.log((xhr.loaded/xhr.total*100)+'% loaded');
            },
            function(error) 
            {
                console.log('An error happened in loadpcd');
            }
        );
    }

}

function loadRobotOctoMap()
{
    var pcd="ROBOT-1";
    var type = "robot";
    var loader = new PCDLoader();
    console.log( "loading pcd for " + type + " " + pcd );
    loader.load(
        "getpcd?id="+pcd+"&type="+type,
        function(mesh) 
        {
            // set size of point and get color from pcd file
            // pass point settings into the mesh
            mesh.material = octoPtsMaterial;
            mesh.scale.set(1,1,1);
            // temporary position settings
            // get centroid values and apply negative offset so pcd displays correctly
            mesh.position.x = 0;
            mesh.position.y = 0;
            mesh.position.z = 0;
            console.log( "adding mesh " +pcd + ", type=" + type);
            scene.add(mesh);

            controls.update();
        },
        function(xhr) 
        {
            console.log((xhr.loaded/xhr.total*100)+'% loaded');
        },
        function(error) 
        {
            console.log('An error happened\n');
        }
    );
}

var world_octomap = null;
function removeWorldOctoMap()
{
    if ( world_octomap )
    {
        scene.remove(world_octomap);
        disposeNode(world_octomap);
        world_octomap = null;
    }
}
function loadWorldOctoMap()
{
    var pcd = "OCTOMAP-1";
    var type = "octomap";
    var loader = new PCDLoader();
    console.log( "loading pcd for " + type + " " + pcd );
    loader.load(
        "getpcd?id="+pcd+"&type="+type,
        function(mesh) 
        {
            // set size of point and get color from pcd file
            // pass point settings into the mesh
            mesh.material = octoPtsMaterial;
            mesh.scale.set(1,1,1);
            // temporary position settings
            // get centroid values and apply negative offset so pcd displays correctly
            mesh.position.x = 0;
            mesh.position.y = 0;
            mesh.position.z = 0;
            console.log( "adding mesh " +pcd + ", type=" + type);
            scene.add(mesh);

            removeWorldOctoMap();//remove previous if exists
            world_octomap = mesh; //set to new

            controls.update();
        },
        function(xhr) 
        {
            console.log((xhr.loaded/xhr.total*100)+'% loaded');
        },
        function(error) 
        {
            console.log('An error happened\n');
        }
    );
}


function loadOctoMapNode(key)
{
    var pcd = "OCTOMAP-"+key;
    var ts = octo_keys[key]["ts"];
    var type = "octomap";
    var loader = new PCDLoader();
    //console.log( "loading pcd for " + type + " " + pcd );
    loader.load(
        "getpcd?id="+pcd+"&type="+type+"&ts="+ts[0]+"-"+ts[1],
        function(mesh) 
        {
            if (!mesh)
            {
                scene.remove(octo_keys[key].obj);
                disposeNode(octo_keys[key].obj);
                octo_keys[key].obj =null; //remove if exists
                //console.log("null pcd");
                return;
            }
            // set size of point and get color from pcd file
            // pass point settings into the mesh
            mesh.material = octoPtsMaterial;
            mesh.scale.set(1,1,1);
            // temporary position settings
            // get centroid values and apply negative offset so pcd displays correctly
            mesh.position.x = 0;
            mesh.position.y = 0;
            mesh.position.z = 0;
            if (octo_keys[key].obj) //already exists, this is an update
            {
                console.log( "updating mesh " +pcd + ", type=" + type);
                scene.remove(octo_keys[key].obj);
                disposeNode(octo_keys[key].obj);
                octo_keys[key].obj = null;
            }
            else
                console.log( "adding mesh " +pcd + ", type=" + type);
            octo_keys[key].obj = mesh;
            scene.add(mesh);
            controls.update();
        },
        function(xhr) 
        {
            //console.log((xhr.loaded/xhr.total*100)+'% loaded');
        },
        function(error) 
        {
            console.log('An error happened\n');
        }
    );

}

function updateWorldMatrices (object)
{
    var parent = object;
    while (parent.parent != null)
    {
        parent.updateMatrixWorld();
        parent = parent.parent;
    }
}
function setCameraFromTo(from,to)
{
    camera.position.set( from.x,from.y,from.z );
    camera.lookAt(to);
    controls.target.copy( to );
    controls.update();
}
function setCameraViewNear(pos)
{
    camera.position.set( pos.x - onemeter*0.25,
                         pos.y - onemeter*0.25,
                         pos.z + onemeter*0.25 );
    controls.target.copy( pos );
    controls.update();
}
function setCameraViewFar(pos)
{
    camera.position.set( pos.x - onemeter,
                         pos.y - onemeter,
                         pos.z+1.5*onemeter );
    controls.target.copy( pos );
    controls.update();
}
function resetCameraPos()
{
    /*
    camera.position.set( allobjects["ROBOT_BASE"].obj_origin.position.x - onemeter,
                         allobjects["ROBOT_BASE"].obj_origin.position.y - onemeter,
                         1.5*onemeter );
    controls.target.copy( allobjects["ROBOT_BASE"].obj_origin.position );
    controls.update();
    */
    lock_viewfromcamera = false;
    var p = allobjects["ROBOT_BASE"].obj_origin.position;
    setCameraViewFar( p );
}
//var floor_displacement_texture = null;
var floor_plane = null;
var floor_color = 0xaaaaaa;
function createFloor()
{
    var floor_texture = new THREE.TextureLoader().load( world.floor.texture );
    floor_texture.wrapS = THREE.RepeatWrapping;
    floor_texture.wrapT = THREE.RepeatWrapping;
    floor_texture.repeat.set( 8, 8 );

    var geometry = new THREE.PlaneBufferGeometry( world.world_size[0],
                                                  world.world_size[1], 32 );
    var material = new THREE.MeshBasicMaterial( {color: floor_color,
                                                 side: THREE.DoubleSide,
                                                 map:floor_texture} );
    var plane = new THREE.Mesh( geometry, material );
    plane.receiveShadow = true;
    plane.position.z = 0; //-(leg_size.upper + leg_size.lower + leg_size.wheel_radius);
    plane.position.x = world.world_size[0] / 2;
    plane.position.y = world.world_size[1] / 2;
        
    scene.add( plane );
}

var origin_axis_length = 75; //default
function createEnv( parent )
{
    createFloor();
    var origin_axis = drawAxis( scene, origin_axis_length );
    addText( origin_axis, "Origin" );

    //plane.material.displacementMap = floor_displacement_texture;
    
    var light = new THREE.PointLight( 0xffffff);
    //light.position.set( world.world_size[0], world.world_size[1], world.world_size[2] );
    light.position.set( mapinfo.height, mapinfo.width, 2500 ); //RG hardcoded height
    light.castsShadow=true;
    scene.add(light);

    light = new THREE.PointLight( 0xffffff );
    light.position.set( 0, 0, 2500 );
    light.castsShadow=true;
    scene.add(light);
    
    light = new THREE.PointLight( 0xffffff );
    //light.position.set( world.world_size[0], 0, world.world_size[2] );
    light.position.set( mapinfo.height, 0, 2500 );
    light.castsShadow=true;
    scene.add(light);

    light = new THREE.PointLight( 0xffffff );
    //light.position.set( 0, world.world_size[1], world.world_size[2] );
    light.position.set( 0, mapinfo.width, 2500 );
    light.castsShadow=true;
    scene.add(light);

    if ( world.hasOwnProperty("objects") )
        loadObjects3D( world.objects );
}

function drawAxis(parent, len)
{
    var axis_len = 75;
    if (len&&len>0)
        axis_len = len;
    var geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( axis_len, 0, 0)
    ]);
    var xaxis = new THREE.Line( geometry, red_line_material );

    geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( 0, axis_len, 0)
    ]);
    var yaxis = new THREE.Line( geometry, green_line_material );

    var geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( 0, 0, axis_len)
    ]);
    var zaxis = new THREE.Line( geometry, blue_line_material );

    var axis = new THREE.Object3D();
    axis.add( xaxis );
    axis.add( yaxis );
    axis.add( zaxis );

    if ( !parent )
        parent = scene;
    parent.add( axis );
    return axis;
}
function drawCOG(parent, len)
{
    var axis_len = 40;
    if (len&&len>0)
        axis_len = len;
    var geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( axis_len, 0, 0)
    ]);
    var xaxis = new THREE.Line( geometry, yellow_line_material );

    geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( 0, axis_len, 0)
    ]);
    var yaxis = new THREE.Line( geometry, yellow_line_material );

    geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3( 0, 0, 0),
        new THREE.Vector3( 0, 0, axis_len)
    ]);
    var zaxis = new THREE.Line( geometry, yellow_line_material );

    var axis = new THREE.Object3D();
    axis.add( xaxis );
    axis.add( yaxis );
    axis.add( zaxis );

    if ( !parent )
        parent = scene;
    parent.add( axis );
    return axis;
}

function drawLine( from, to, color )
{
    var material = line_materials[color];
    if ( !material )
    {
        material = new THREE.LineBasicMaterial({
	        color: color
        });
        line_materials[color] = material;
    }

    var points = [];
    points.push( new THREE.Vector3( from[0], from[1], from[2] ) );
    points.push( new THREE.Vector3( to[0], to[1], to[2] ) );
    var geometry = new THREE.BufferGeometry().setFromPoints( points );
    var line = new THREE.Line( geometry, material );
    scene.add( line );
    return line;
}

function drawLabelledLine( from, to, color, label )
{
    if (!label )
        label = "p";

    var material = line_materials[color];
    if ( !material )
    {
        material = new THREE.LineBasicMaterial({
	        color: color
        });
        line_materials[color] = material;
    }

    var obj = new THREE.Object3D();

    var points = [];
    points.push( new THREE.Vector3( from[0], from[1], from[2] ) );
    points.push( new THREE.Vector3( to[0], to[1], to[2] ) );
    var geometry = new THREE.BufferGeometry().setFromPoints( points );
    var line = new THREE.Line( geometry, material );
    obj.add(line);

    geometry = new THREE.SphereBufferGeometry( 10, 8, 8 );
    var p1 = new THREE.Mesh(geometry, getMaterial(color));
    addText(p1, label+"1",color);
    p1.position.fromArray(from);
    obj.add(p1);

    var p2 = new THREE.Mesh(geometry, getMaterial(color));
    addText(p2, label+"2",color);
    p2.position.fromArray(to);
    obj.add(p2);


    scene.add(obj);

    return obj;
}




function getTranslation(o)
{
    return (o.hasOwnProperty("translation") ? o["translation"] : (o.hasOwnProperty("t") ? o["t"] : null ) );
}
function getRotation(o)
{
    return (o.hasOwnProperty("rotation") ? o["rotation"] : (o.hasOwnProperty("r") ? o["r"] : null ) );
}

function getPCD(o)
{
    return (o.hasOwnProperty("pcd") ? o["pcd"] : null );
}

function getPCDType(o)
{
    return (o.hasOwnProperty("type") ? o["type"] : null );
}

function loadTranslation(obj,o)
{
    var t = getTranslation(o);
    if (t)
    {
        obj.position.fromArray(t);
        if( t.length>3)
        {
            var unit = 1.0;
            if( t[3] == "in" )
                unit = inch2mm;
            else if ( t[3] == "cm" )
                unit = 10.0;
            else if ( t[3] == "m" )
                unit = 1000.0
            obj.position.multiplyScalar(unit);
        }
    }
}

function loadRotation(obj,o)
{
    var r = getRotation(o);
    if (r)
    {
        var unit = d2r;
        var order = "XYZ"; //default
        if ( r.length>3 )
            order = r[3];
        obj.rotation.set( r[0]*unit, r[1]*unit, r[2]*unit, order );
    }
}
function loadOrigin(obj,o)
{
    if (o.hasOwnProperty("origin"))
    {
        loadTranslation(obj,o.origin);
        loadRotation(obj, o.origin);
        return true;
    }
    return false;
}

function parseVal(v)
{
    if(typeof v == "string" )
    {
        var unit = 1.0;
        if ( (k=v.indexOf("in")) > 0 )
        {
            unit = oneinch;
        }
        else if ( (k=v.indexOf("mm")) > 0 )
        {
            unit = 1.0;
        }
        else if ( (k=v.indexOf("cm")) > 0 )
        {
            unit = 10.0;
        }
        else if ( (k=v.indexOf("m")) > 0 )
        {
            unit = 1000.0;
        }
        if(k>0)
            v = v.substring(0,k);
        return parseFloat(v) * unit;
    }
    return v;
}
function getShape(o)
{
    //returns same if obj
    //else if string, finds in shape list
    if ( (typeof o).toLowerCase() == "object" )
    {
        //if base shape, then good, else recurse
        if (o["type"] == "box" || o["type"]=="cylinder")
            return o;
        else
        {
            //console.log(o);
            //get user shape def named by type, then merge override props into that
            var parent = {};
            mergeInto(parent, getShape(o["type"])); //copy over props since dont want to modify original
            var type = parent["type"];
            //merge everything into parent, except the "type"
            mergeInto(parent,o);
            parent["type"] = type; //restore
            return getShape(parent);
        }
    }
    if (world.hasOwnProperty("shapes") &&
        world.shapes.hasOwnProperty(o))
        return getShape(world.shapes[o]);
    return null;
}
var vorigin = new THREE.Vector3(0,0,0); //frequently needed

function createShape(obj, o, p)
{
    var shape = null;
    var geometry = null;
    if (o.hasOwnProperty("shape"))
    {
        var shapeinfo = getShape( o.shape );
        if (!shapeinfo)
        {
            console.log("ERROR: Shape data not found ");
            console.log(o.shape);
            return;
        }
        var material = null;
        if ( shapeinfo.hasOwnProperty("texture"))
        {
            //material = getTextureMaterial( shapeinfo.texture );
            material = new THREE.MeshBasicMaterial ( {map:getTexture(shapeinfo.texture)} );
            obj["tex"] = shapeinfo.texture; //save the name
        }
        else
            material = getMaterialAlpha( getProp(shapeinfo,"color", "black"),
                                         getProp(shapeinfo, "opacity", "1" ) );

        //we need to get the right orientation of the cylinder
        //from origin to endpoint
        var orientation = new THREE.Matrix4();
        if (p)
            orientation.lookAt( vorigin, p, scene.up );
        if(shapeinfo.type=="cylinder")
        {
            var diameter=parseVal(getProp(shapeinfo, "diameter",oneinch) );
            var length = (p ? p.length() : parseVal(getProp(shapeinfo,"length",oneinch)));
            geometry = new THREE.CylinderBufferGeometry( diameter/2, diameter/2, length, 32 );
            var yoffset = parseVal( getProp(shapeinfo,"yoffset",0) );
            if(p)
                geometry.translate( 0,(length/2)+yoffset, 0);  //make the bottom end of the cylinder the origin to make it a link
            else
                geometry.translate( 0,yoffset, 0); 
            var axis = getProp(shapeinfo,"axis","z");
            if(axis == "z")
                geometry.rotateX( -Math.PI/2);
            else if ( axis == "x" )
                geometry.rotateZ( -Math.PI/2);
        }
        else if(shapeinfo.type=="box")
        {
            var width=parseVal( getProp(shapeinfo, "xwidth",oneinch) );
            var height=parseVal( getProp(shapeinfo, "yheight",oneinch) );
            var depth = (p ? p.length() : parseVal(getProp(shapeinfo,"zdepth",oneinch)));
            geometry = new THREE.BoxBufferGeometry( width, height, depth );
            //first translate, then rotate
            if(p)
                geometry.translate( 0,0,-depth/2); //only if endpoint
            //geometry.rotateX( -Math.PI/2);
        }
        if (geometry)
        {
            shape = new THREE.Mesh( geometry, material );
            if(p)
                shape.applyMatrix4(orientation);
            obj.add(shape);
            obj.shapeobj = shape; //save it
        }
    }
    /*
    if (p && !shape)
    {
        //add a line to obj_link from origin to endpoint
        geometry = new THREE.Geometry();
        geometry.vertices.push(new THREE.Vector3( 0, 0, 0) );
        geometry.vertices.push(p);
        var line = new THREE.Line(geometry, black_line_material);
        obj.add(line);
    }
    */
}

function loadEndpoint(o,t)
{
    if(t.hasOwnProperty("endpoint"))
    {
        loadTranslation(o.obj_endpoint, t.endpoint);
        loadRotation(o.obj_link, t.endpoint);
        return true;
    }
    return false;
}

function loadCOG(o,t)
{
    var ret = false;
    if(t.hasOwnProperty("cog"))
    {
        if ( !o.hasOwnProperty( "obj_cog" ) )
        {
            o.obj_cog = new THREE.Object3D();
            ret = true;
        }
        loadTranslation(o.obj_cog, t["cog"] );
        return ret;
    }
    return false;
}

function checkShowAxis(obj,o)
{
    if (o.hasOwnProperty("showaxis") && o.showaxis)
    {
        drawAxis(obj);
    }
}
function checkShowCOG(obj,o,name)
{
    if (o.hasOwnProperty("show") && o.show)
    {
        var axisobj = drawCOG(obj);
        if (o.hasOwnProperty("showname") && o.showname)
            addTextSmall(axisobj, "CG-"+name, "yellow" );
    }
}
function addText(obj,txt,color)
{
    var mesh = getTextMesh(txt,color);
    obj.add(mesh);
    return mesh;
}
function addTextSmall(obj,txt,color)
{
    var mesh = getTextMesh(txt,color, 20);
    obj.add(mesh);
    return mesh;
}
function checkShowName(o,obj)
{
    if (o.hasOwnProperty("showname") && o.showname)
    {
        o["textmesh"] = addText(obj,o.name);
    }
}

function object3DExists(id)
{
    return allobjects.hasOwnProperty(id);
}

function object3D(id)
{
    return (allobjects.hasOwnProperty(id) ? allobjects[id] : "");
}

function mergeInto(obj, src) {
    Object.keys(src).forEach(function(key) { if ( src.hasOwnProperty(key) ) obj[key] = src[key]; });
    //Object.keys(src).forEach(function(key) { obj[key] = src[key]; });
    return obj;
}
//we need a function to load the object3d objects correctly
//main problem is they could be read out of order
//with child being read before parent
//lets do in two passes
function loadObjects3D(objs)
{
    for(var id in objs )
    {
        if (!objs.hasOwnProperty(id)) continue;
        if ( id == "WORLD" )
            continue;

        var o = objs[id];
        //objects for orgin, link, and endpoint
        o.obj_origin = new THREE.Object3D();
        o.obj_origin.name = o.name+"-Origin"; 
        checkShowName(o,o.obj_origin);
        if( loadOrigin(o.obj_origin, o) )
        {   //has origin
            createShape(o.obj_origin, o.origin);
            checkShowAxis(o.obj_origin, o.origin);
            loadPCD(o.obj_origin, o.origin,o);
            //disposeHierarchy(objs, disposeNode);
        }

        o.obj_link = new THREE.Object3D();
        o.obj_link.name = o.name+"-Link";

        o.obj_endpoint = new THREE.Object3D();
        o.obj_endpoint.name = o.name+"-Endpoint";

        //add geometry to link if needed
        //then add endpoint obj to link at
        //endpoint position
        //so then, endpoint rotation acts on link
        //and position acts on endpoint
        if ( loadEndpoint(o,o) &&
             getTranslation(o.endpoint) != null )
        {
            createShape(o.obj_link,
                        o.endpoint,
                        o.obj_endpoint.position );
            checkShowAxis(o.obj_endpoint, o.endpoint);
        }

        o.obj_link.add( o.obj_endpoint );
        o.obj_origin.add( o.obj_link );

        if ( loadCOG( o, o ) )
        {
            checkShowCOG( o.obj_cog, o.cog, o.name );
            o.obj_link.add( o.obj_cog );
        }

        //we have to add o.obj_origin to its parent
        //but we dont yet know if its loaded, so in next pass
    }

    mergeInto( allobjects, objs ); //merge into all objects before searching for parents
    //add objects to their parents
    for(var id in objs)
    {
        if ( id == "WORLD" )
            continue;
        if (!allobjects.hasOwnProperty(id)) continue;

        var o = allobjects[id];
        if (o.parent_id == "WORLD")
            scene.add(o.obj_origin);
        else
            allobjects[o.parent_id].obj_endpoint.add(o.obj_origin);

//        if (id.indexOf("ROBOT_BASE") >= 0 )
//            console.log( "Hello" );

//        if (id.indexOf("POSMARKER") >= 0 )
//            console.log( "HelloTHERE" );
    }
}

function processUpdates(transforms)
{
    for(var id in transforms)
    {
        if(!transforms.hasOwnProperty(id))
            continue;
        var t = transforms[id];
        var obj = allobjects[id];
        if ( !obj )
            console.log( "obj is null for " + id );
        if(loadOrigin(obj.obj_origin, t) && obj.hasOwnProperty("origin"))
        {
            loadPCD(obj.obj_origin, obj.origin, obj);
        }
        loadEndpoint(obj,t);
        if ( loadCOG( obj, obj ) )
        {
            checkShowCOG( obj.obj_cog, obj.cog,obj.name );
            obj.obj_link.add( obj.obj_cog );
        }
        if ( hasProp(t, "name") && obj.name != t.name )
        {
            console.log( obj.name + " is " + t.name );
            var mesh = obj["textmesh"];
            if (mesh)
            {
                console.log( "removing mesh" );
                obj.obj_origin.remove( mesh );
                disposeNode( mesh );
                mesh = null;
            }
            checkShowName(t,obj.obj_origin);
        }
        //check texture change
        if ( obj.hasOwnProperty("origin") )
        {
            var o=obj["origin"];
            if (o.hasOwnProperty("shape"))
            {
                var shapeinfo = getShape( o.shape );
                if ( shapeinfo.hasOwnProperty("texture"))
                {
                    if ( shapeinfo["texture"] != obj.obj_origin["tex"] )
                    {
                        //console.log( "updating texture from " + obj.obj_origin["tex"] + " to " + shapeinfo["texture"] );
                        var old_tex = obj.obj_origin.shapeobj.material.map;
                        var new_tex = getTexture( shapeinfo.texture,
                                                  obj.obj_origin.shapeobj.material );
                        //obj.obj_origin.shapeobj.material.map = new_tex;
                        //obj.obj_origin.shapeobj.material.needsUpdate = true;
                        removeTexture( obj.obj_origin["tex"] );
                        obj.obj_origin["tex"] = shapeinfo.texture; //save the name
                        disposeNode( old_tex );
                        old_tex = null;
                    }
                }
            }
        }


        mergeInto( obj, t ); //copy all props
    }
}


