// Changes the RGB/HEX temporarily to a HSL-Value, modifies that value
// and changes it back to RGB/HEX.

function shiftColor(img, color) {
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    //console.log(img, img.width);
    var myData = ctx.getImageData(0, 0, img.width, img.height);

    var referenceColor = {h: 120, s: 0.2, l: 0.5};
    var desiredColor = rgbToHSL(color);

    var hDiff = desiredColor.h - referenceColor.h;
    var sRatio = desiredColor.s / referenceColor.s;
    var lRatio = desiredColor.l / referenceColor.l;

    for (var i = 0; i < myData.data.length; i += 4) {
        let r = myData.data[i];
        let g = myData.data[i + 1];
        let b = myData.data[i + 2];
        let alpha = myData.data[i + 3];
        if (alpha <= 0) {
            continue;
        }
        myData.data[i + 3] = 255;


        let hsl = rgbToHSL_direct(r / 255.0, g / 255.0, b / 255.0);
        if (!(hsl.h > 110 && hsl.h <= 125))
            continue;

        hsl.h = (hsl.h + hDiff + 360) % 360;
        hsl.l = hsl.l * lRatio;
        hsl.s = hsl.s * sRatio;
        hsl.l = Math.min(1.0, hsl.l);
        hsl.s = Math.min(1.0, hsl.s);

        let res = hslToRGB_direct(hsl);
        res = [res.r, res.g, res.b];
        //res = [0, 0, 0];

        myData.data[i] = res[0];
        myData.data[i + 1] = res[1];
        myData.data[i + 2] = res[2];
    }

    ctx.putImageData(myData, 0, 0);


    var resultImage = new Image();
    resultImage.isLoaded = false;
    resultImage.onload = function () {
        resultImage.isLoaded = true;
    };
    resultImage.src = canvas.toDataURL();
    return resultImage;
}

function changeHue(rgb, degree) {
    var hsl = rgbToHSL(rgb);
    hsl.h += degree;
    if (hsl.h > 360) {
        hsl.h -= 360;
    } else if (hsl.h < 0) {
        hsl.h += 360;
    }
    return hslToRGB(hsl);
}

// exepcts a string and returns an object
function rgbToHSL(rgb) {
    // strip the leading # if it's there
    rgb = rgb.replace(/^\s*#|\s*$/g, '');

    // convert 3 char codes --> 6, e.g. `E0F` --> `EE00FF`
    if (rgb.length == 3) {
        rgb = rgb.replace(/(.)/g, '$1$1');
    }

    var r = parseInt(rgb.substr(0, 2), 16) / 255,
        g = parseInt(rgb.substr(2, 2), 16) / 255,
        b = parseInt(rgb.substr(4, 2), 16) / 255;

    return rgbToHSL_direct(r, g, b);
}

function rgbToHSL_direct(r, g, b) {
    let cMax = Math.max(r, g, b),
        cMin = Math.min(r, g, b),
        delta = cMax - cMin,
        l = (cMax + cMin) / 2,
        h = 0,
        s = 0;

    if (delta === 0) {
        h = 0;
    } else if (cMax === r) {
        h = 60 * (((g - b) / delta) % 6);
    } else if (cMax === g) {
        h = 60 * (((b - r) / delta) + 2);
    } else {
        h = 60 * (((r - g) / delta) + 4);
    }

    if (delta === 0) {
        s = 0;
    } else {
        s = (delta / (1 - Math.abs(2 * l - 1)))
    }

    return {
        h: h,
        s: s,
        l: l
    }
}

// expects an object and returns a string
function hslToRGB_direct(hsl) {
    let h = hsl.h,
        s = hsl.s,
        l = hsl.l,
        c = (1 - Math.abs(2 * l - 1)) * s,
        x = c * (1 - Math.abs((h / 60) % 2 - 1)),
        m = l - c / 2,
        r, g, b;

    if (h < 60) {
        r = c;
        g = x;
        b = 0;
    } else if (h < 120) {
        r = x;
        g = c;
        b = 0;
    } else if (h < 180) {
        r = 0;
        g = c;
        b = x;
    } else if (h < 240) {
        r = 0;
        g = x;
        b = c;
    } else if (h < 300) {
        r = x;
        g = 0;
        b = c;
    } else {
        r = c;
        g = 0;
        b = x;
    }

    r = normalize_rgb_value(r, m);
    g = normalize_rgb_value(g, m);
    b = normalize_rgb_value(b, m);

    return {
        r: r,
        g: g,
        b: b
    }
}

function hslToRGB(hsl) {
    let c = hslToRGB_direct(hsl);
    return rgbToHex(c.r, c.g, c.b);
}

function normalize_rgb_value(color, m) {
    color = Math.floor((color + m) * 255);
    if (color < 0) {
        color = 0;
    }
    return color;
}

function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}