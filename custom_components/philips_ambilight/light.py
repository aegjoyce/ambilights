

import json
import string
import requests
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import logging
import time

from homeassistant.components.light import (ATTR_BRIGHTNESS, LightEntity, PLATFORM_SCHEMA, ATTR_HS_COLOR, SUPPORT_BRIGHTNESS, SUPPORT_COLOR, ATTR_EFFECT, SUPPORT_EFFECT)
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_USERNAME, CONF_PASSWORD)
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

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

AMBILIGHT_EFFECT_LIST = [EFFECT_MANUAL, EFFECT_FV_STANDARD, EFFECT_FV_NATURAL, EFFECT_FV_IMMERSIVE, EFFECT_FV_VIVID, 
                        EFFECT_FV_GAME, EFFECT_FV_COMFORT, EFFECT_FV_RELAX, EFFECT_FA_ADAP_BRIGHTNESS, EFFECT_FA_ADAP_COLOR,
                        EFFECT_FA_RETRO, EFFECT_FA_SPECTRUM, EFFECT_FA_SCANNER_CLOCKWISE, EFFECT_FA_SCANNER_ALTERNATING, EFFECT_FA_RHYTHM, EFFECT_FA_RANDOM, 
                        EFFECT_LL_HOT_LAVA, EFFECT_LL_DEEP_WATER, EFFECT_LL_FRESH_NATURE, EFFECT_LL_ISF, EFFECT_LL_CUSTOM_COLOR]

DEFAULT_DEVICE = 'default'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_USER = 'user'
DEFAULT_PASS = 'pass'
DEFAULT_NAME = 'TV Ambilights'
BASE_URL = 'https://{0}:1926/6/{1}'
DEFAULT_HUE = 360
DEFAULT_SATURATION = 0
DEFAULT_BRIGHTNESS = 255
DEFAULT_EFFECT = EFFECT_MANUAL
TIMEOUT = 1
OLD_STATE = [DEFAULT_HUE, DEFAULT_SATURATION, DEFAULT_BRIGHTNESS, DEFAULT_EFFECT]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
	vol.Required(CONF_USERNAME, default=DEFAULT_USER): cv.string,
	vol.Required(CONF_PASSWORD, default=DEFAULT_PASS): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})

def setup_platform(hass, config, add_devices, discovery_info=None):
	name = config.get(CONF_NAME)
	host = config.get(CONF_HOST)
	user = config.get(CONF_USERNAME)
	password = config.get(CONF_PASSWORD)
	add_devices([Ambilight(name, host, user, password)])

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
        if ATTR_BRIGHTNESS in kwargs or ATTR_HS_COLOR in kwargs:
            state = self._state
            if state == False:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"}):
                    return False
          
            if ATTR_BRIGHTNESS in kwargs:
                brightness = kwargs[ATTR_BRIGHTNESS]
                convertedBrightness = int(brightness/2)
            elif self._brightness:
                convertedBrightness = int(self._brightness/2)
            else:
                convertedBrightness = int(DEFAULT_BRIGHTNESS/2)
            
            if ATTR_HS_COLOR in kwargs:
                hs = kwargs[ATTR_HS_COLOR]
                convertedHue = int(hs[0]*(255/360))
                convertedSaturation = int(hs[1]*(255/100))
            elif self._hs:
                convertedHue = int(self._hs[0]*(255/360))
                convertedSaturation = int(self._hs[1]*(255/100))
            else:
                convertedHue = DEFAULT_HUE
                convertedSaturation = DEFAULT_SATURATION
            
            if not self._postReq('ambilight/lounge',{"color":{"hue":convertedHue,"saturation":convertedSaturation,"brightness":convertedBrightness},"colordelta":{"hue":0,"saturation":0,"brightness":0},"speed":0} ):
                return False
            
            if ATTR_BRIGHTNESS in kwargs:
                self._brightness = kwargs[ATTR_BRIGHTNESS]
            if ATTR_HS_COLOR in kwargs:
                self._hs = kwargs[ATTR_HS_COLOR]
        
        elif ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            if effect == EFFECT_MANUAL:
                state = self._state
                if state == False:
                    if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"}):
                        return False
            else:
                if not self._postReq('ambilight/power', {'power':'Off'}):
                    return False
            self.set_effect(effect)
        
        else:
            if OLD_STATE[3] == EFFECT_MANUAL:
                state = self._state
                if state == False:
                    if self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"}):
                        if not self._postReq('ambilight/lounge',{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),"brightness":int(OLD_STATE[2]/2)},"colordelta":{"hue":0,"saturation":0,"brightness":0},"speed":0} ):
                            return False
            else: 
                effect = self._effect
                self.set_effect(effect)

    def turn_off(self, **kwargs):
        state = self._state
        hs = self._hs
        brightness = self._brightness
        effect = self._effect
        if state == True:
            if hs == None:
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
            if brightness == None:
                self._brightness = DEFAULT_BRIGHTNESS
            if effect == None:
                self._effect = DEFAULT_EFFECT
            global OLD_STATE
            OLD_STATE = [self._hs[0], self._hs[1], self._brightness, self._effect]
        if effect == EFFECT_MANUAL:
            if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"}):
                return False
        if not self._postReq('ambilight/power', {'power':'Off'}):
            return False
        self._state = False
		
    def getState(self):
        fullState = self._getReq('ambilight/currentconfiguration')
        if fullState:
            self._available = True
            styleName = fullState['styleName']
            
            if styleName == "OFF":
                self._state = False

            elif styleName == "Lounge light":
                self._state = True
                isExpert = fullState['isExpert']
                
                if isExpert == False:
                    effectName = fullState['menuSetting']
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS
                    if effectName == "HOT_LAVA":
                        self._effect = EFFECT_LL_HOT_LAVA
                    elif effectName == "DEEP_WATER":
                        self._effect = EFFECT_LL_DEEP_WATER
                    elif effectName == "FRESH_NATURE":
                        self._effect = EFFECT_LL_FRESH_NATURE
                    elif effectName == "ISF":
                        self._effect = EFFECT_LL_ISF
                    elif effectName == "CUSTOM_COLOR":
                        self._effect = EFFECT_LL_CUSTOM_COLOR

                elif isExpert == True:
                    hue = fullState['colorSettings']['color']['hue']
                    saturation = fullState['colorSettings']['color']['saturation']
                    bright = fullState['colorSettings']['color']['brightness']
                    if (hue + saturation + bright) == 0:
                        if not self._state:
                            self.turn_off
                        else:
                            kwargs = {ATTR_EFFECT: self._effect, ATTR_BRIGHTNESS: self._brightness, ATTR_HS_COLOR: self._hs}
                            self.turn_on(**kwargs)
                        return False
                    else:
                        self._hs = (hue*(360/255),saturation*(100/255))
                        self._brightness = bright*2
                        self._effect = EFFECT_MANUAL
                
                else:
                    self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                    self._brightness = DEFAULT_BRIGHTNESS

            elif styleName == 'FOLLOW_VIDEO':
                self._state = True
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                self._brightness = DEFAULT_BRIGHTNESS
                effectName = fullState['menuSetting']
                if effectName == "STANDARD":
                    self._effect = EFFECT_FV_STANDARD
                elif effectName == "NATURAL":
                    self._effect = EFFECT_FV_NATURAL
                elif effectName == "IMMERSIVE":
                    self._effect = EFFECT_FV_IMMERSIVE
                elif effectName == "VIVID":
                    self._effect = EFFECT_FV_VIVID
                elif effectName == "GAME":
                    self._effect = EFFECT_FV_GAME
                elif effectName == "COMFORT":
                    self._effect = EFFECT_FV_COMFORT
                elif effectName == "RELAX":
                    self._effect = EFFECT_FV_RELAX
                
            elif styleName == 'FOLLOW_AUDIO':
                self._state = True
                self._hs = (DEFAULT_HUE, DEFAULT_SATURATION)
                self._brightness = DEFAULT_BRIGHTNESS
                effectName = fullState['menuSetting']
                if effectName == "VU_METER":
                    self._effect = EFFECT_FA_RETRO
                elif effectName == "ENERGY_ADAPTIVE_BRIGHTNESS":
                    self._effect = EFFECT_FA_ADAP_BRIGHTNESS
                elif effectName == "ENERGY_ADAPTIVE_COLORS":
                    self._effect = EFFECT_FA_ADAP_COLOR  
                elif effectName == "SPECTUM_ANALYSER":
                    self._effect = EFFECT_FA_SPECTRUM
                elif effectName == "KNIGHT_RIDER_CLOCKWISE":
                    self._effect = EFFECT_FA_SCANNER_CLOCKWISE
                elif effectName == "KNIGHT_RIDER_ALTERNATING":
                    self._effect = EFFECT_FA_SCANNER_ALTERNATING
                elif effectName == "RANDOM_PIXEL_FLASH":
                    self._effect = EFFECT_FA_RHYTHM
                elif effectName == "MODE_RANDOM":
                    self._effect = EFFECT_FA_RANDOM

        else:
            self._available = False
            self._state = False

    def update(self):
        self.getState()

    def set_effect(self, effect):
        if effect:
            if effect == EFFECT_MANUAL:
                if not self._postReq('ambilight/lounge',{"color":{"hue":int(OLD_STATE[0]*(255/360)),"saturation":int(OLD_STATE[1]*(255/100)),"brightness":OLD_STATE[2]},"colordelta":{"hue":0,"saturation":0,"brightness":0},"speed":0} ):
                    return False
                self._hs = (OLD_STATE[0], OLD_STATE[1])
                self._brightness = OLD_STATE[2]
            elif effect == EFFECT_FV_STANDARD:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"STANDARD"}):
                    return False
            elif effect == EFFECT_FV_NATURAL:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"NATURAL"}):
                    return False
            elif effect == EFFECT_FV_IMMERSIVE:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"IMMERSIVE"}):
                    return False
            elif effect == EFFECT_FV_VIVID:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"VIVID"}):
                    return False
            elif effect == EFFECT_FV_GAME:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"GAME"}):
                    return False
            elif effect == EFFECT_FV_COMFORT:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"COMFORT"}):
                    return False
            elif effect == EFFECT_FV_RELAX:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_VIDEO","isExpert":False,"menuSetting":"RELAX"}):
                    return False
            elif effect == EFFECT_FA_ADAP_BRIGHTNESS:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_BRIGHTNESS"}):
                    return False
            elif effect == EFFECT_FA_ADAP_COLOR:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"ENERGY_ADAPTIVE_COLORS"}):
                    return False
            elif effect == EFFECT_FA_RETRO:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"VU_METER"}):
                    return False
            elif effect == EFFECT_FA_SPECTRUM:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"SPECTRUM_ANALYSER"}):
                    return False
            elif effect == EFFECT_FA_SCANNER_CLOCKWISE:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"KNIGHT_RIDER_CLOCKWISE"}):
                    return False
            elif effect == EFFECT_FA_SCANNER_ALTERNATING:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"KNIGHT_RIDER_ALTERNATING"}):
                    return False
            elif effect == EFFECT_FA_RHYTHM:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"RANDOM_PIXEL_FLASH"}):
                    return False
            elif effect == EFFECT_FA_RANDOM:
                if not self._postReq('ambilight/currentconfiguration', {"styleName":"FOLLOW_AUDIO","isExpert":False,"menuSetting":"MODE_RANDOM"}):
                    return False
            elif effect == EFFECT_LL_HOT_LAVA:
                if not self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":201}}}]}):
                    return False
            elif effect == EFFECT_LL_DEEP_WATER:
                if not self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":202}}}]}):
                    return False
            elif effect == EFFECT_LL_FRESH_NATURE:
                if not self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":203}}}]}):
                    return False
            elif effect == EFFECT_LL_ISF:
                if not self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":207}}}]}):
                    return False
            elif effect == EFFECT_LL_CUSTOM_COLOR:
                if not self._postReq('menuitems/settings/update', {"values":[{"value":{"Nodeid":2131230770,"Controllable":"true","Available":"true","data":{"selected_item":208}}}]}):
                    return False
        self._effect = effect
                
    def _getReq(self, path):
        for _ in range(3):
            try:
                response = requests.get(BASE_URL.format(self._host, path), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
                if response.ok:
                    self.on = True
                    return json.loads(response.text)
            except requests.exceptions.RequestException as e:
                self.on = False
                time.sleep(1)
        return False

    def _postReq(self, path, data):
        for _ in range(3):
            try:
                response = requests.post(BASE_URL.format(self._host, path), data=json.dumps(data), verify=False, auth=HTTPDigestAuth(self._user, self._password), timeout=TIMEOUT)
                if response.ok:
                    self.on = True
                    return True
            except requests.exceptions.RequestException as e:
                self.on = False
                time.sleep(1)
        return False