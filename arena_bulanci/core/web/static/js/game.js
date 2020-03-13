let BULLET_SPEED = 5;
let PLAYER_SIZE = 3;
let PLAYER_BOUNDING_BOX_SIZE = 2.1;
let TICKS_PER_SECOND = 15;
let SHOW_DEBUG_INFO = false;
const AMMO_BAR_LEN = 1.0;
const AMMO_BAR_FILL_LEN = 0.7;
const AMMO_BAR_HEIGHT = 0.2;

let mapWidth = 160;
let mapHeight = 90;

let obstacleBoxes = [
    [120.5, 12.3, 3.5],
    [91, 40, 7],
    [83.5, 41.5, 4],
    [89, 76, 4.5],
    [135, 59, 4.5],
    [40, 53, 3.7],
    [36, 55.5, 3.7],
    [31.5, 59, 3.7],
    [21, 41, 4],
    [15, 15, 4.5],
    [57, 22, 13]
];

let PLAYER_SPRITES = getSpriteSet();
let MAP_BACKGROUND = new Image();
MAP_BACKGROUND.src = "/static/na_dobrou_noc.png";
let MAP_BACKGROUND_MASK = new Image();
MAP_BACKGROUND_MASK.src = "/static/na_dobrou_noc_mask.png";

let ANIMATION_OFFSETS = {};
let DEAD_PLAYERS = {};
let KNOWN_BULLETS = {};

class Game {
    constructor(state, prevGame) {
        this.tick = state._tick;
        this.tickTime = Date.now();
        this.players = state._players;
        this.sortedPlayers = this._sortPlayers(this.players);
        this.bullets = state._bullets;
        this.prevGame = prevGame;

        let imageSize = PLAYER_SIZE * 4 + 4;
        let center = imageSize / 2;

        this.imageSize = imageSize;
        this.center = center;

        this.defaultPlayerColor = rgbToHex(252, 186, 3);
    }

    render(ctx) {
        if (this.prevGame === null) {
            return;
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "white";
        //ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(MAP_BACKGROUND, 0, 0, mapWidth, mapHeight);

        let currentTime = Date.now();
        let timeFromLastTick = currentTime - this.tickTime;
        let partialTick = Math.min(1.0, timeFromLastTick / 1000.0 * TICKS_PER_SECOND);

        this._renderDeaths(ctx, currentTime);
        this._renderBullets(ctx, partialTick);
        this._renderPlayers(ctx, partialTick, currentTime);
        this._renderObstacles(ctx);
    }

    _renderObstacles(ctx) {
        ctx.drawImage(MAP_BACKGROUND_MASK, 0, 0, mapWidth, mapHeight);

        let showObstacleBoxes = SHOW_DEBUG_INFO;
        if (showObstacleBoxes) {
            for (let obstacleBox of obstacleBoxes) {
                ctx.beginPath();
                ctx.arc(obstacleBox[0], obstacleBox[1], obstacleBox[2], 0, 2 * Math.PI);
                ctx.lineWidth = 0.05;
                ctx.fillStyle = 'lightblue';
                ctx.fill();
                ctx.stroke();
            }
        }
    }

    _renderPlayers(ctx, partialTick, currentTime) {
        const showBoundingBox = SHOW_DEBUG_INFO;
        for (let player of this.sortedPlayers) {
            let player_id = player.id;
            let playerRgb = this._parseTuple(player.color);
            let playerColor = this.defaultPlayerColor;
            if (playerRgb !== undefined) {
                playerColor = rgbToHex(playerRgb[0], playerRgb[1], playerRgb[2]);
            }

            let old_player = this.prevGame.players[player_id];
            let position = this._parseTuple(player.position);

            if (showBoundingBox) {
                ctx.beginPath();
                ctx.arc(position[0], position[1], PLAYER_BOUNDING_BOX_SIZE, 0, 2 * Math.PI);
                ctx.lineWidth = 0;
                ctx.fillStyle = '#777';
                ctx.fill();
            }

            if (old_player !== undefined) {
                position = [position[0], position[1]];
                let old_position = this._parseTuple(old_player.position);
                let dx = position[0] - old_position[0];
                let dy = position[1] - old_position[1];

                if (dx === 0 && dy === 0) {
                    ANIMATION_OFFSETS[player_id] = currentTime;
                } else {
                    //console.log(player_id, position);
                }

                position[0] = old_position[0] + partialTick * dx;
                position[1] = old_position[1] + partialTick * dy;
            }

            let animationTime = currentTime - (ANIMATION_OFFSETS[player_id] || 0);
            let index = Math.round(animationTime / 50);

            ctx.font = "1.5px Georgia";
            ctx.fillStyle = 'lightblue';
            ctx.textAlign = "center";
            let playerName = player_id.split("@");
            ctx.fillText(playerName[0], position[0], position[1] - PLAYER_SIZE - 1.3);


            let img = PLAYER_SPRITES.getWalking(playerColor, player._direction, index);
            if (img !== null) {
                ctx.drawImage(img, position[0] - this.center, position[1] - this.center, this.imageSize, this.imageSize);
            }

            for (let i = 0; i < player.gun.ammo_count; ++i) {
                ctx.beginPath();
                let s = position[0] + i * AMMO_BAR_LEN;
                let e = s + AMMO_BAR_FILL_LEN;
                let y = position[1] - PLAYER_SIZE - 1.2 + 3 * AMMO_BAR_HEIGHT;
                let offset = AMMO_BAR_LEN * player.gun.full_ammo_count / 2;
                ctx.strokeStyle = 'lightblue';
                ctx.lineWidth = AMMO_BAR_HEIGHT;
                ctx.moveTo(s - offset, y);
                ctx.lineTo(e - offset, y);
                ctx.stroke();
            }

        }
    }

    _renderBullets(ctx, partialTick) {
        const showRays = SHOW_DEBUG_INFO;
        const rayLen = 200;
        for (let bullet_id in this.bullets) {
            let bullet = this.bullets[bullet_id];
            let position = this._parseTuple(bullet.start_position);
            let distance = (this.tick - bullet.start_tick + partialTick - 0.7) * BULLET_SPEED;
            let coords = this._parseTuple(bullet.direction_coords);

            if (KNOWN_BULLETS[bullet_id] === undefined) {
                let audio = document.createElement("audio");
                audio.src = "/static/audio/revolver.mp3";
                audio.play().catch(() => true);
                KNOWN_BULLETS[bullet_id] = true;
            }

            let p = position;
            if (showRays) {
                ctx.moveTo(p[0], p[1]);
                ctx.lineTo(p[0] + coords[0] * rayLen, p[1] + coords[1] * rayLen);
                ctx.stroke();
            }

            p = [p[0] + coords[0] * distance, p[1] + coords[1] * distance];
            ctx.beginPath();
            ctx.arc(p[0], p[1], 0.15, 0, 2 * Math.PI);
            ctx.lineWidth = 0;
            ctx.strokeStyle = 'orange';
            ctx.fill();
            ctx.stroke();
        }

        for (let bullet_id in KNOWN_BULLETS) {
            if (this.bullets[bullet_id] === undefined)
                delete KNOWN_BULLETS[bullet_id];
        }
    }

    _renderDeaths(ctx, currentTime) {
        for (let player_id in this.prevGame.players) {
            if (this.players[player_id] !== undefined) {
                continue;
            }

            DEAD_PLAYERS[player_id] = this.prevGame.players[player_id];
            DEAD_PLAYERS[player_id].deathTime = currentTime;
        }

        const animationFrameCount = 21;
        const fadeOutFrameCount = 10;
        const animationSpeedFactor = 1 / 100;
        const fadeOutTime = (fadeOutFrameCount + 1) / animationSpeedFactor;
        for (let player_id in DEAD_PLAYERS) {
            delete this.prevGame.players[player_id];
            let deadPlayer = DEAD_PLAYERS[player_id];
            let playerRgb = this._parseTuple(deadPlayer.color);
            let playerColor = this.defaultPlayerColor;
            if (playerRgb !== undefined) {
                playerColor = rgbToHex(playerRgb[0], playerRgb[1], playerRgb[2]);
            }
            let timeFromDeath = currentTime - deadPlayer.deathTime;
            let index = Math.round(timeFromDeath * animationSpeedFactor);
            if (index > animationFrameCount + fadeOutFrameCount) {
                delete DEAD_PLAYERS[player_id];
                continue;
            }

            if (index > animationFrameCount) {
                let timeFromFadeOutStart = timeFromDeath - animationFrameCount / animationSpeedFactor;
                ctx.globalAlpha = 1 - timeFromFadeOutStart / fadeOutTime;
            }

            let position = this._parseTuple(deadPlayer.position);
            let img = PLAYER_SPRITES.getDeath(playerColor, deadPlayer.direction, Math.min(index, animationFrameCount));
            if (img !== null) {
                ctx.drawImage(img, position[0] - this.center, position[1] - this.center, this.imageSize, this.imageSize);
            }
            ctx.globalAlpha = 1.0;
        }
    }

    _parseTuple(positionData) {
        if (positionData == undefined) {
            return undefined;
        }
        return positionData["py/tuple"];
    }

    _sortPlayers(players) {
        let result = [];
        for (let playerId in players) {
            let player = players[playerId];

            result.push(player);
        }

        let self = this;
        let key = function (player) {
            return self._parseTuple(player.position)[0]
        };
        result.sort(function (a, b) {
            return key(a) < key(b) ? -1 : (a === b ? 0 : 1);
        });
        return result;
    }
}

