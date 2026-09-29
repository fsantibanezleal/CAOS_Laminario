# U16 · The deployment · requirements

The shared interface requirements (R-080, R-084, R-085) and the tile-server requirements of U3, U10 and U11 (R-086,
R-1105, R-1106, the tray's thumbnails) are checked again on the live site; R-1601 to R-1606 are this unit's own.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs (LAMINARIO_GATE_ORIGIN set to the live site)

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs (live)

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs (live)

R-086  WHEN a micro asset has a pixel size, THE stage viewer SHALL show a scale bar whose length matches the physical distance within 1 percent at every objective step.
       Gate: frontend/gates/scalebar.mjs (live)

R-1601  THE site SHALL answer only over HTTPS at laminario.ml.fasl-work.com, redirecting plain HTTP, with the certificate renewed by the host.
        Gate: frontend/gates/production.mjs

R-1602  THE API, the worker, tusd and iipsrv SHALL listen on loopback only (8147, 8148, 8149), and THE internal routes SHALL not be reachable from outside.
        Gate: frontend/gates/production.mjs

R-1603  THE live site SHALL hold the base collection as its bake was validated: every slide of the lock published, every stored file equal to its manifest's SHA-256.
        Gate: frontend/gates/production.mjs

R-1604  WHEN a tile is requested twice, THE second answer SHALL come from the cache with the same bytes, and A tile of an unpublished image SHALL be refused.
        Gate: frontend/gates/production.mjs

R-1605  THE web app's hashed assets SHALL be cached for a year and its index never, and every address the app routes SHALL answer with the app.
        Gate: frontend/gates/production.mjs

R-1606  THE deployment SHALL be reproducible from the repository: an install script for the code, its environment, the database and the site, and a separate registration script for the long-running services.
        Gate: frontend/gates/production.mjs (the version served equals the tag installed)
```
