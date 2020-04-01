class SpriteData {
    constructor(color, walkingImages, deathImages) {
        this.walkingImages = walkingImages;
        this.deathImages = deathImages;
        this._isReady = false;
    }

    isReady() {
        if (this._isReady) {
            return true;
        }

        for (let i = 0; i < this.walkingImages.length; ++i) {
            for (let j = 0; j < this.walkingImages[i].length; ++j) {
                if (!this.walkingImages[i][j].isLoaded) {
                    return false;
                }
            }
        }

        for (let i = 0; i < this.deathImages.length; ++i) {
            if (!this.deathImages[i].isLoaded) {
                return false;
            }
        }

        this._isReady = true;
    }
}

class PlayerSpriteSet {
    constructor(baseWalkingImages, baseDeathImages) {
        this._baseWalkingImages = baseWalkingImages;
        this._baseDeathImages = baseDeathImages;

        this._baseSpriteData = new SpriteData(null, this._baseWalkingImages, this._baseDeathImages);

        this._colors = {}
    }

    isReady(color) {
        if (!this._baseSpriteData.isReady())
            return false;

        if (this._colors[color] === undefined) {
            // create the new set
            let walkingImages = [];
            for (let i = 0; i < this._baseWalkingImages.length; ++i) {
                let buffer = [];
                walkingImages.push(buffer);
                for (let j = 0; j < this._baseWalkingImages[i].length; ++j) {
                    buffer.push(shiftColor(this._baseWalkingImages[i][j], color));
                }
            }

            let deathImages = [];
            for (let i = 0; i < this._baseDeathImages.length; ++i) {
                deathImages.push(shiftColor(this._baseDeathImages[i], color));
            }

            this._colors[color] = new SpriteData(color, walkingImages, deathImages);
        }

        return this._colors[color].isReady();
    }

    getWalking(color, direction, index) {
        if (!this.isReady(color)) {
            return null;
        }

        let imgs = this._colors[color].walkingImages[direction];
        return imgs[index % imgs.length];
    }

    getDeath(color, direction, index) {
        if (!this.isReady(color)) {
            return null;
        }

        let imgs = this._colors[color].deathImages;
        return imgs[index % imgs.length];
    }
}

function getSpriteSet() {
    let walking = [];
    for (let dir = 0; dir < 4; ++dir) {
        let animation = [];
        walking[dir] = animation;
        for (let i = 0; i < 8; ++i) {
            let imageObj = new Image();
            imageObj.isLoaded = false;
            imageObj.onload = function () {
                imageObj.isLoaded = true;
            };

            let src;
            if (dir === 3) {
                src = `/static/bulanci/b_d3/${('000' + i).substr(-3)}.png`;
            } else {
                src = `/static/bulanci/b_d${dir}_${i}.png`;
            }
            imageObj.src = src;
            animation.push(imageObj);
        }
    }

    let deaths = [];
    for (let i = 0; i < 22; ++i) {
        let imageObj = new Image();
        imageObj.isLoaded = false;
        imageObj.onload = function () {
            imageObj.isLoaded = true;
        };
        imageObj.src = `/static/bulanci/d_d3/${('000' + i).substr(-3)}.png`;
        deaths.push(imageObj);
    }

    return new PlayerSpriteSet(walking, deaths);
}