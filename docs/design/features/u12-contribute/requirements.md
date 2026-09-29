# U12 · Contribute · requirements

R-087 is from the design document and is this unit's; R-080, R-084, R-085 and R-089 are shared by the interface units,
and U12 adds the account places and the contribute place to their gates. R-1201 to R-1208 are this unit's own.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-087  WHEN a contributor adds a photo with GPS, THE contribute flow SHALL show the location before upload and SHALL strip it when geoprivacy is private.
       Gate: frontend/gates/contribute.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1201  THE account places SHALL sign in, register from an invitation link, request and complete a password reset, and sign out through the account API, and WHILE someone is signed in THE masthead SHALL name the account.
        Gate: frontend/gates/contribute.mjs

R-1202  EVERY validation error and flag of a slide case SHALL carry a stable code and its parameters, and THE contribute place SHALL show it next to the field it names in the page's language.
        Gate: tests/contracts/test_error_codes.py

R-1203  WHEN a file of a case whose geoprivacy is private still carries a GPS position, THE verification SHALL refuse it and say why.
        Gate: tests/uploads/test_location.py

R-1204  THE location routine SHALL remove the GPS position and every XMP packet from JPEG, PNG, WebP and TIFF files and SHALL keep their image data, date and orientation.
        Gate: frontend/src/contribute/location.test.ts

R-1205  A slide case SHALL go from draft to processing only when its contributor submits it and every image has its file, from processing to published only when every image is verified and processed, and back to draft with the reason when an image fails.
        Gate: tests/contribute/test_lifecycle.py

R-1206  A contributor SHALL list, reopen, change and delete their own drafts, and SHALL NOT read or change anyone else's.
        Gate: tests/contribute/test_lifecycle.py

R-1207  WHEN a pixel size is calibrated from two points a known length apart, THE flow SHALL give the length over the distance in pixels and its uncertainty of one pixel at each end.
        Gate: frontend/src/contribute/calibration.test.ts

R-1208  WHEN a contributor fills a case by pointer with a real scanner file and a photograph, THE file SHALL reach the server through tus, be verified and processed, and THE slide SHALL be published and open at its address with the file's SHA-256.
        Gate: frontend/gates/contribute.mjs
```
