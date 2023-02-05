### Home Assistant Platform to integrate Phillip TVs' Ambilight as a light entity using the JointSpace API ###
### 2021 rework by ajoyce ###


import json
import string
import requests
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging

from homeassistant.components.light import (ATTR_BRIGHTNESS, LightEntity, PLATFORM_SCHEMA, ATTR_HS_COLOR, ATTR_TRANSITION,
                                            SUPPORT_BRIGHTNESS, SUPPORT_COLOR, SUPPORT_TRANSITION, ATTR_EFFECT, SUPPORT_EFFECT)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD)
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'TV Ambilights'
BASE_URL = 'https://{0}:1926/6/{1}' # for older Philips TVs, try changing this to 'http://{0}:1925/1/{1}'
DEFAULT_HUE = 360
DEFAULT_SATURATION = 0
DEFAULT_BRIGHTNESS = 255
TIMEOUT = 5.0


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Required(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

# Effect names. Some may not be accessible in your TV menu, but may still work via this integration

EFFECT_MANUAL = "Manual"
EFFECT_FV_STANDARD = "Standard"
EFFECT_FV_NATURAL = "Natural"
EFFECT_FV_IMMERSIVE = "Sports"
EFFECT_FV_VIVID = "Vivid"
EFFECT_FV_GAME = "Game"
EFFECT_FV_COMFORT = "Comfort"
EFFECT_FV_RELAX = "Relax"
EFFECT_FA_ADAP_BRIGHTNESS = "Lumina"
EFFECT_FA_ADAP_COLOR = "Colora"
EFFECT_FA_RETRO = "Retro"
EFFECT_FA_SPECTRUM = "Spectrum"
EFFECT_FA_SCANNER_CLOCKWISE = "Scanner (clockwise)"
EFFECT_FA_SCANNER_ALTERNATING = "Scanner (alternating)"
EFFECT_FA_RHYTHM = "Rhythm"
EFFECT_FA_RANDOM = "Party"
EFFECT_LL_HOT_LAVA = "Hot Lava"
EFFECT_LL_DEEP_WATER = "Deep Water"
EFFECT_LL_FRESH_NATURE = "Fresh Nature"
EFFECT_LL_ISF = "Warm White"
EFFECT_LL_CUSTOM_COLOR = "Custom Color"
DEFAULT_EFFECT = EFFECT_MANUAL

# Effect name list. You can safely remove any effects from the list below to remove them from the frontend

AMBILIGHT_EFFECT_LIST = [EFFECT_MANUAL, EFFECT_FV_STANDARD, EFFECT_FV_NATURAL, EFFECT_FV_IMMERSIVE, EFFECT_FV_VIVID, 
                        EFFECT_FV_GAME, EFFECT_FV_COMFORT, EFFECT_FV_RELAX, EFFECT_FA_ADAP_BRIGHTNESS, EFFECT_FA_ADAP_COLOR,
                        EFFECT_FA_RETRO, EFFECT_FA_SPECTRUM, EFFECT_FA_SCANNER_CLOCKWISE, EFFECT_FA_SCANNER_ALTERNATING, EFFECT_FA_RHYTHM, EFFECT_FA_RANDOM, 
                        EFFECT_LL_HOT_LAVA, EFFECT_LL_DEEP_WATER, EFFECT_LL_FRESH_NATURE, EFFECT_LL_ISF, EFFECT_LL_CUSTOM_COLOR]

def setup_platform(hass, config, add_devices, discovery_info=None):
	name = config.get(CONF_NAME)
	host = config.get(CONF_HOST)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	add_devices([Ambilight(name, host, user, password)])

OLD_STATE = [DEFAULT_HUE, DEFAULT_SATURATION, DEFAULT_BRIGHTNESS, DEFAULT_EFFECT]

class Ambilight(LightEntity):

    def __init__(self, name, host, user, password):
        self._name = name
        self._host = host
        self._user = user
        self._password = password
        self._state = None
        self._brightness = None
        self._hs = None
        self._available = False
        self._effect = None
        self._session = requests.Session()
        self._session.mount('https://', HTTPAdapter(pool_connections=1))


    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    @property
    def available(self):
        return self._available

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR | SUPPORT_EFFECT

    @property
    def effect_list(self):
        return AMBILIGHT_EFFECT_LIST

    @property
    def brightness(self):
        return self._brightness

    @property
    def hs_color(self):
        return self._hs

    @property
    def effect(self):
        return self._effect

    @property
    def should_poll(self):
        return True

    def turn_on(self, **kwargs):
        if ATTR_TRANSITION in kwargs:
            # Here we save current color and brightness
            convertedBrightness_old = self._brightness
            convertedHue_old = int(self._hs[0]*(255/360))
            convertedSaturation_old = int(self._hs[1]*(255/100))

            # if ATTR_BRIGHTNESS in kwargs:
            #     convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            # else:
            #     convertedBrightness = self._brightness
            
            # if ATTR_HS_COLOR in kwargs:
            #     convertedHue = int(ATTR_HS_COLOR[0]*(255/360))
            #     convertedSaturation = int(ATTR_HS_COLOR[1]*(255/100))
            # else:
            #     convertedHue = int(self._hs[0]*(255/360))
            #     convertedSaturation = int(self._hs[1]*(255/100))
            
            # hue_addorsubst = 1 if (convertedHue_old < convertedHue) else -1
            # saturation_addorsubst = 1 if (convertedSaturation_old < convertedSaturation) else -1
            # brightness_addorsubst = 1 if (convertedBrightness_old < convertedBrightness) else -1

            # # Now we start transition from old color/brightness to new color and brightness. Loop until match.
            # while convertedBrightness_old != convertedBrightness or convertedHue_old != convertedHue or convertedSaturation_old != convertedSaturation:
            #     convertedBrightness_old = (convertedBrightness_old + brightness_addorsubst) if convertedBrightness_old != convertedBrightness else convertedBrightness
            #     convertedHue_old = (convertedHue_old + hue_addorsubst) if convertedHue_old != convertedHue else convertedHue
            #     convertedSaturation_old = (convertedSaturation_old + saturation_addorsubst) if convertedSaturation_old != convertedSaturation else convertedSaturation
            #     self._postReq('ambilight/lounge',{"color":{"hue":convertedHue_old,"saturation":convertedSaturation_old,"brightness":convertedBrightness_old}} )
            # self.getState()

        elif ATTR_HS_COLOR in kwargs:
            self._hs = kwargs[ATTR_HS_COLOR]
            convertedHue = int(self._hs[0]*(255/360))
            convertedSaturation = int(self._hs[1]*(255/100))
            if ATTR_BRIGHTNESS in kwargs:
                convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            else:
                convertedBrightness = self._brightness
            self._postReq('ambilight/lounge',{"color":{"hue":convertedHue,"saturation":convertedSaturation,"brightness":convertedBrightness}} )

        elif ATTR_BRIGHTNESS in kwargs:
            # use this section instead if you cannot change the brightness without the bulb changing colour
            # (brightness commands are limited to integer values 1:10)
            #convertedBrightness = int(10*(kwargs[ATTR_BRIGHTNESS])/255)
            #self._postReq('menuitems/settings/update', "values": [{"value": {"Nodeid": 2131230769, "Controllable": "true", "Available": "true", "string_id": "Brightness", "data": {"value": convertedBrightness}}}]} )
            # and comment out all of the following
            
            convertedBrightness = kwargs[ATTR_BRIGHTNESS]
            self._postReq('ambilight/lounge',{"color":{"hue":int(self._hs[0]*(255/360)),"saturation":int(self._hs[1]*(255/100)),"brightness":convertedBrightness}} )

        elif ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            self.set_effect(effect)

        else:
            if OLD_STATE[3] == EFFECT_MANUAL:
                self._postReq('ambilight/lounge',{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),"brightness":OLD_STATE[2]}} )
            else: 
                effect = self._effect
                self.set_effect(effect)

    def turn_off(self, **kwargs):
        self.getState()
        state = self._state
        if state == True:
            hs = self._hs
            if hs == None:
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
            brightness = self._brightness
            if brightness == None:
                self._brightness = DEFAULT_BRIGHTNESS
            effect = self._effect
            if effect == None:
                self._effect = DEFAULT_EFFECT
            global OLD_STATE
            OLD_STATE = [self._hs[0], self._hs[1], self._brightness, self._effect]
            self._postReq('ambilight/power', {'power':'Off'})
        self._state = False
		
    def getState(self):
        fullstate = self._getReq('ambilight/currentconfiguration')
        if fullstate:
            self._available = True
            styleName = fullstate['styleName']
            
            if styleName == "OFF":
                self._state = False

            elif styleName == "Lounge light":
                self._state = True
                isExpert = fullstate['isExpert']
                
                if isExpert == False:
                    effect = fullstate['menuSetting']
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS
                    if effect == "HOT_LAVA":
                        self._effect = EFFECT_LL_HOT_LAVA
                    elif effect == "DEEP_WATER":
                        self._effect = EFFECT_LL_DEEP_WATER
                    elif effect == "FRESH_NATURE":
                        self._effect = EFFECT_LL_FRESH_NATURE
                    elif effect == "ISF":
                        self._effect = EFFECT_LL_ISF
                    elif effect == "CUSTOM_COLOR":
                        self._effect = EFFECT_LL_CUSTOM_COLOR

                elif isExpert == True:
                    hue = fullstate['colorSettings']['color']['hue']
                    saturation = fullstate['colorSettings']['color']['saturation']
                    bright = fullstate['colorSettings']['color']['brightness']
                    self._hs = (hue*(360/255),saturation*(100/255))
                    self._brightness = bright
                    self._effect = EFFECT_MANUAL
                
                else:
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS

            elif styleName == 'FOLLOW_VIDEO':
                self._state = True
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                self._brightness = DEFAULT_BRIGHTNESS
                effect = fullstate['menuSetting']
                if effect == "STANDARD":
                    self._effect = EFFECT_FV_STANDARD
                elif effect == "NATURAL":
                    self._effect = EFFECT_FV_NATURAL
                elif effect == "IMMERSIVE":
                    self._effect = EFFECT_FV_IMMERSIVE
                elif effect == "VIVID":
                    self._effect = EFFECT_FV_VIVID
                elif effect == "GAME":
                    self._effect = EFFECT_FV_GAME
                elif effect == "COMFORT":
                    self._effect = EFFECT_FV_COMFORT
                elif effect == "RELAX":
                    self._effect = EFFECT_FV_RELAX
                
            elif styleName == 'FOLLOW_AUDIO':
                self._state = True
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                self._brightness = DEFAULT_BRIGHTNESS
                effect = fullstate['menuSetting']
                if effect == "VU_METER":
                    self._effect = EFFECT_FA_RETRO
                elif effect == "ENERGY_ADAPTIVE_BRIGHTNESS":
                    self._effect = EFFECT_FA_ADAP_BRIGHTNESS
                elif effect == "ENERGY_ADAPTIVE_COLORS":
                    self._effect = EFFECT_FA_ADAP_COLOR  
                elif effect == "SPECTUM_ANALYSER":
                    self._effect = EFFECT_FA_SPECTRUM
                elif effect == "KNIGHT_RIDER_CLOCKWISE":
                    self._effect = EFFECT_FA_SCANNER_CLOCKWISE
                elif effect == "KNIGHT_RIDER_ALTERNATING":
                    self._effect = EFFECT_FA_SCANNER_ALTERNATING
                elif effect == "RANDOM_PIXEL_FLASH":
                    self._effect = EFFECT_FA_RHYTHM
                elif effect == "MODE_RANDOM":
                    self._effect = EFFECT_FA_RANDOM

        else:
            self._available = False
            self._state = False

    def update(self):
        self.getState()

    def set_effect(self, effect):
        if effect:
            if effect == EFFECT_MANUAL:
                self._postReq('ambilight/lounge',{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),"brightness":OLD_STATE[2]}} )
                self._hs = (OLD_STATE[0], OLD_STATE[1])
                self._brightness = OLD_STATE[2]
            elif effect == EFFECT_FV_STANDARD:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"STANDARD"})
            elif effect == EFFECT_FV_NATURAL:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"})
            elif effect == EFFECT_FV_IMMERSIVE:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"IMMERSIVE"})
            elif effect == EFFECT_FV_VIVID:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"VIVID"})
            elif effect == EFFECT_FV_GAME:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"GAME"})
            elif effect == EFFECT_FV_COMFORT:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"COMFORT"})
            elif effect == EFFECT_FV_RELAX:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"RELAX"})
            elif effect == EFFECT_FA_ADAP_BRIGHTNESS:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_BRIGHTNESS"})
            elif effect == EFFECT_FA_ADAP_COLOR:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_COLORS"})
            elif effect == EFFECT_FA_RETRO:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"VU_METER"})
            elif effect == EFFECT_FA_SPECTRUM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"SPECTRUM_ANALYSER"})
            elif effect == EFFECT_FA_SCANNER_CLOCKWISE:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"KNIGHT_RIDER_CLOCKWISE"})
            elif effect == EFFECT_FA_SCANNER_ALTERNATING:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"KNIGHT_RIDER_ALTERNATING"})
            elif effect == EFFECT_FA_RHYTHM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"RANDOM_PIXEL_FLASH"})
            elif effect == EFFECT_FA_RANDOM:
                self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"MODE_RANDOM"})
            elif effect == EFFECT_LL_HOT_LAVA:
                self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":201}}}]})
            elif effect == EFFECT_LL_DEEP_WATER:
                self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":202}}}]})
            elif effect == EFFECT_LL_FRESH_NATURE:
                self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":203}}}]})
            elif effect == EFFECT_LL_ISF:
                self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":207}}}]})
            elif effect == EFFECT_LL_CUSTOM_COLOR:
                self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":208}}}]})
        self.update()
                
    def _getReq(self, path):
        success = False
        attempts = 0
        while attempts < 3 and not success:
            try:
                resp = self._session.get(BASE_URL.format(self._host, path), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
                self.on = True
                success = True
                return json.loads(resp.text)
            except requests.exceptions.HTTPError as err:
                _LOGGER.warning("GET error: %s", err)
                self.on = False
                attempts += 1
                return False
            except requests.exceptions.RequestException as err:
                _LOGGER.warning("GET error: %s", err)
                self.on = False
                attempts += 1
                return False

    def _postReq(self, path, data):
        success = False
        attempts = 0
        while attempts < 3 and not success:
            try:
                resp = self._session.post(BASE_URL.format(self._host, path), data=json.dumps(data), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
                self.on = True
                success = True
            except requests.exceptions.HTTPError as err:
                _LOGGER.warning("POST error: %s", err)
                self.on = False
                attempts += 1
                return False
            except requests.exceptions.RequestException as err:
                _LOGGER.warning("POST error: %s", err)
                self.on = False
                attempts += 1
                return False
