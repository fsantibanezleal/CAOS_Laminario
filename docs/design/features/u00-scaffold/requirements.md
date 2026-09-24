# U0 · Scaffold · requirements

The product-level requirements R-001 to R-004 (content standards, repository hygiene, CI budget, no Pages
workflow) live in the [design document](../../SDD.md), section 9. This unit adds the requirement below.

```
R-008  WHEN a client requests GET /api/health, THE API SHALL answer 200 with the product name and the version held in the VERSION file.
       Gate: tests/test_health.py::test_health_reports_product_and_version
```
