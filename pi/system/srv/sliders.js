/*******************************************************
 * Copyright (C) 2020 onwards
 * Evodyne Robotics Corporation / Evodyne Robotics Academy
 * support@evodyneacademy.com
 * Can not be copied and/or distributed under any
 * circumstances, directly or
 * indirectly, verbatim or modified or derived or 'inspired'
 *******************************************************/

var sliders = {
    inited: false,
    maxDiff: 100,
    dragStart: null,
    s: null,
    min: 0,
    max: 0,
    range: null,
    size: 0,
    sliderIdx: 0,
    lastIdx: 0,
    title: null
};

let oldDiff = 0;

var initPositionSliders = function() {
    sliders = {
        inited: false,
        maxDiff: 100,
        dragStart: null,
        s: null,
        min: 0,
        max: 0,
        range: null,
        size: 0,
        sliderIdx: 0,
        lastIdx: 0,
        title: "pos"
    };
    oldDiff = 0;
    sliders.inited = false;
    console.log("position sliders init")
    if (sliders.inited) {
        console.log("sliders iniited")
        return;
    }
    if (did("poscontrol").style.display == "none") {
        console.log("returned");
        return;
    }

    sliders.inited = true;
    sliders.s = [
        { id: "sliderfla", slider: $("sliderfla"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderflh", slider: $("sliderflh"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderflk", slider: $("sliderflk"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfra", slider: $("sliderfra"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfrh", slider: $("sliderfrh"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfrk", slider: $("sliderfrk"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbla", slider: $("sliderbla"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderblh", slider: $("sliderblh"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderblk", slider: $("sliderblk"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbra", slider: $("sliderbra"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbrh", slider: $("sliderbrh"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbrk", slider: $("sliderbrk"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 }

    ];


    sliders.range = $("slidersize");
    sliders.size = sliders.range.offsetWidth;
    sliders.min = -(sliders.size / 2) + 15;
    sliders.max = sliders.size / 2;
    var mid = 0;

    for (var i = 0; i < sliders.s.length; i++) {
        sliders.s[i].slider.addEventListener('mousedown', sliderHandleMouseDown);
        sliders.s[i].slider.addEventListener('touchstart', sliderHandleMouseDown);
        sliders.s[i].slider.style.transform = `translate3d(${mid}px,0px,0px)`;
    }
    document.addEventListener('mousemove', sliderHandleMouseMove);
    document.addEventListener('touchmove', sliderHandleMouseMove);

    document.addEventListener('mouseup', sliderHandleMouseUp);
    document.addEventListener('touchend', sliderHandleMouseUp);
    // setInterval(() => console.log(((getLastMovedSliderPosition() / (sliders.size)) * 175) + 90), 300);
    // setInterval(() => console.log(getLastMovedSliderPosition()), 300);
    // setInterval("bringBack()", 100);
}

var initCoordinateSliders = function() {
    sliders = {
        inited: false,
        maxDiff: 100,
        dragStart: null,
        s: null,
        min: 0,
        max: 0,
        range: null,
        size: 0,
        sliderIdx: 0,
        lastIdx: 0,
        title: "coor"
    };
    sliders.inited = false;
    oldDiff = 0;

    console.log("coordinate sliders init")

    if (sliders.inited) {
        console.log("sliders iniited")
        return;
    }

    if (did("coorcontrol").style.display == "none") {
        console.log("returned");
        return;
    }

    sliders.inited = true;
    sliders.s = [
        { id: "sliderflz", slider: $("sliderflz"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfly", slider: $("sliderfly"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderflx", slider: $("sliderflx"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfrz", slider: $("sliderfrz"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfry", slider: $("sliderfry"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderfrx", slider: $("sliderfrx"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderblz", slider: $("sliderblz"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbly", slider: $("sliderbly"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderblx", slider: $("sliderblx"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbrz", slider: $("sliderbrz"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbry", slider: $("sliderbry"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 },
        { id: "sliderbrx", slider: $("sliderbrx"), x: 0, lastX: 0, moved: true, "invert": false, actualX: 0 }
    ];


    sliders.range = $("slidersizecoor");
    sliders.size = sliders.range.offsetWidth;
    sliders.min = -(sliders.size / 2);
    sliders.max = sliders.size / 2;
    var mid = 0;

    for (var i = 0; i < sliders.s.length; i++) {
        sliders.s[i].slider.addEventListener('mousedown', sliderHandleMouseDown);
        sliders.s[i].slider.addEventListener('touchstart', sliderHandleMouseDown);
        sliders.s[i].slider.style.transform = `translate3d(${mid}px,0px,0px)`;
    }
    document.addEventListener('mousemove', sliderHandleMouseMove);
    document.addEventListener('touchmove', sliderHandleMouseMove);

    document.addEventListener('mouseup', sliderHandleMouseUp);
    document.addEventListener('touchend', sliderHandleMouseUp);
    // setInterval(() => console.log(((getLastMovedSliderPosition() / (sliders.size)) * 175) + 90), 300);
    // setInterval(() => console.log(getLastMovedSliderPosition()), 300);
    // setInterval("bringBack()", 100);
}

function sliderHandleMouseDown(event) {
    for (var i = 0; i < sliders.s.length; i++) {
        if (sliders.s[i].id == event.target.id)
            sliders.sliderIdx = i;
    }

    sliders.s[sliders.sliderIdx].slider.style.transition = '0s';

    if (event.changedTouches) {
        sliders.dragStart = {
            x: event.changedTouches[0].clientX,
            y: 0
        };
        console.log("test")
        return;
    }
    sliders.dragStart = {
        x: event.clientX,
        y: 0
    };
        //console.log(event.clientX);
}

function sliderHandleMouseMove(event) {
    //console.log("moved");
    if (sliders.dragStart === null) return;
    event.preventDefault();
    if (event.changedTouches) {
        event.clientX = event.changedTouches[0].clientX;

    }

    const xDiff = event.clientX - sliders.dragStart.x;
    const distance = Math.min(sliders.maxDiff, sliders.xDiff);
    var s = sliders.s[sliders.sliderIdx];


    s.x = Math.min(sliders.max, xDiff + s.lastX);
    s.x = Math.max(sliders.min, s.x);
    s.x = xDiff + s.lastX;
    if (s.x > sliders.max) {
        s.x = sliders.max;
    }
    if (s.x < sliders.min) {
        s.x = sliders.min;
    }
    if (Math.abs(xDiff) - Math.abs(oldDiff) < 35) {} else {

        console.log(xDiff)
    }
    console.log(Math.abs(xDiff) - Math.abs(oldDiff))
    oldDiff = xDiff
    s.slider.style.transform = `translate3d(${sliders.s[sliders.sliderIdx].x}px, 0px, 0px)`;
    s.moved = true;
}

function sliderHandleMouseUp(event) {
    if (sliders.dragStart === null) return;
    //stick.style.transition = '.2s';
    //sliders[sliderIdx].slider.transform = `translate3d(75px, 75px, 0px)`;
    var s = sliders.s[sliders.sliderIdx];
    s.actualX = s.x;
    if (sliders.title = "coor" && (sliders.sliderIdx == 1 || sliders.sliderIdx == 4 || sliders.sliderIdx == 7 || sliders.sliderIdx == 10)) {
        s.actualX += 230;
    }
    sendSliderCommands(sliders.sliderIdx)
    s.lastX = s.x;
    sliders.dragStart = null;
}

function getLastMovedSliderPosition() {
    return sliders.s[sliders.sliderIdx].x;
}

function bringBack() {
    //bring back toward center when released
    if (sliders.dragStart !== null)
        return; //something is being moved
    for (i = 0; i < sliders.s.length; i++) {
        var s = sliders.s[i];
        if (s.x == 0)
            continue;
        if (s.x < 0) {
            s.x += 40;
            if (s.x > 0)
                s.x = 0; //went past
        } else if (s.x > 0) {
            s.x -= 40;
            if (s.x < 0)
                s.x = 0;
        }
        s.lastX = s.x;
        s.slider.style.transform = `translate3d(${s.x}px, 0px, 0px)`;
        s.moved = true;
    }
}

function getSliderPosIfMoved(i) {
    var s = sliders.s[sliders.sliderIdx];
    var r = { "moved": !s.moved, "pos": s.x };
    s.moved = false;
    return r;
}