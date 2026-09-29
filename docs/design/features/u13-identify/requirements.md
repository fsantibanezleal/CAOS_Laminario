# U13 · Identify · requirements

R-088 is from the design document and is this unit's; R-080, R-084, R-085 and R-089 are shared by the interface units,
and U13 adds the Identify and moderation places to their gates. R-1301 to R-1309 are this unit's own. The research is
dossier 15 of the planning record.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-088  THE agreement rule SHALL set the community anchor to the deepest node on which more than two thirds of identifications agree.
       Gate: tests/community/test_agreement.py::test_scenario_table

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1301  WHEN an account with the identify capability adds an identification to a published slide, THE identification SHALL become that account's only current one on the slide, and the account SHALL be able to withdraw it and restore it.
        Gate: tests/community/test_identifications.py

R-1302  WHEN an identification names an ancestor of the slide's anchor, THE identifier SHALL say whether it disagrees with the finer anchor, and THE disagreement SHALL count against every node from the ancestor's child down to that anchor.
        Gate: tests/community/test_agreement.py::test_scenario_table

R-1303  WHEN the community anchor changes, THE slide's anchor SHALL become the community anchor, and THE slide SHALL keep its drawer when the drawer accepts the new anchor, and SHALL otherwise move to the tree's suggestion.
        Gate: tests/community/test_follow.py

R-1304  THE badge SHALL be verified when every slide check passes and the community anchor is at the depth its kind needs (or, when the community has voted the anchor as good as it can be, at the coarser depth its kind allows), reference when a check fails or the vote leaves an anchor coarser than that, and needs ID otherwise; a change of the community anchor SHALL reset the votes.
        Gate: tests/community/test_quality.py

R-1305  EVERY signed-in account SHALL be able to flag a slide, an identification or an annotation with a category and a comment, and THE curators SHALL list open flags and resolve each with a comment.
        Gate: tests/community/test_moderation.py

R-1306  WHEN a curator hides a slide, an identification or an annotation with a reason of at least 10 characters, THE item SHALL leave every public listing, count, search, map, manifest and the agreement, its author SHALL see the reason, and only that curator or an admin SHALL restore it; every action SHALL be recorded.
        Gate: tests/community/test_moderation.py

R-1307  THE Identify place SHALL list the published slides that need identification, filtered by collection and kind, leaving out the slides the account has identified when asked to.
        Gate: tests/community/test_queue.py

R-1308  WHEN two identifiers agree with a contributed slide's anchor in the browser, THE slide SHALL become verified; WHEN a curator hides it, a visitor SHALL no longer find it and its contributor SHALL see why; WHEN the curator restores it, it SHALL be back.
        Gate: frontend/gates/identify.mjs

R-1309  EVERY published slide SHALL carry its first identification: the contributor's anchor for a contribution, the source's determination for a base slide.
        Gate: tests/community/test_identifications.py
```
