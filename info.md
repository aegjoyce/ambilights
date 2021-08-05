# Philips TV Ambilight Component for Home Assistant

An updated version of jomwells Ambilight component. I had been having issues with the official Home Assistant Philips TV JS integratation causing my TV to crash so have reverted to using ADB and jomwells' old integration.

It has required significant rewriting but now works very well with no errors on my 55OLED804.

## Notable updates:

> - Changed HTTPS requests for effect changes to the official protocol, sniffed from the Philips TV Remote app. This means all Lounge Light modes are properly called now
> - Corrections to parsing of current effect mode to avoid NoneType errors
> - Added polling - scan interval is 30s by default but can be changed
> - Fixed NoneType not subscriptable error caused by a light.turn_off command when no hs/brightness/effect data had previously been cached
> - Added Scanner (clockwise) mode

Please try it out and let me know if it works for you!
