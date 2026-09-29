# U5 · Resumable uploads · requirements

R-040 to R-043 moved here verbatim from the design document. R-501 to R-503 are this unit's own.

```
R-040  WHEN an upload is interrupted and resumed, THE upload SHALL complete with the original SHA-256.
       Gate: tests/uploads/test_tus.py::test_resume_after_interruption

R-041  IF an upload's sniffed type is not in the ingestion contract, THEN THE system SHALL delete it from quarantine and report the type.
       Gate: tests/uploads/test_tus.py::test_disallowed_type_rejected

R-042  IF an upload would exceed the contributor's byte or WSI quota, THEN THE hook SHALL refuse creation.
       Gate: tests/uploads/test_tus.py::test_quota_refused

R-043  WHILE the data volume holds more than 90 percent of its size, THE system SHALL refuse new WSI uploads and say why.
       Gate: tests/uploads/test_tus.py::test_tier_a_budget_blocks_wsi

R-501  THE upload server's compose file SHALL run the pinned tusd image on loopback with a read-only root and its hooks reaching the API with the session forwarded.
       Gate: tests/uploads/test_tus.py::test_tusd_compose_file_on_loopback

R-502  THE hook SHALL refuse an upload from a visitor, into another contributor's slide case, for an unknown image, or while another upload for the same image is in progress.
       Gate: tests/uploads/test_tus.py::test_uploads_are_authorised

R-503  WHEN a ZIP archive is uploaded, THE verification SHALL accept it only when it holds an MRXS, VSI or DICOM slide.
       Gate: tests/uploads/test_tus.py::test_archives_are_recognised
```
