# company equipment manual discovery, research only

Source inventories: `company_Equipment_Consolidated_FINAL_2026-09-21.xlsx` (Master Detail) and `company_PM_Tracker_Site_Baseline_2026-10-02.xlsx` (Machines, PM_Sources). Master identifies 47 source asset rows expanded to 65 tracked machine instances (64 active). Inventory remains private; do not publish serial numbers or full site asset register.

## Initial candidate references, not verified to serial number

| Equipment | Reference | Status |
|---|---|---|
| Hurco VM3 / VM series | https://support.hurco.com/ | OEM support portal; exact edition to verify |
| Hurco VM series maintenance | https://www.manualslib.com/products/Hurco-Vm-Series-12403384.html | Third-party candidate; model and revision not yet verified |
| Edwards 50-ton ironworker | https://cansaw.com/support.html | Distributor provides 50-ton manual; exact machine model/version verify |
| Edwards ironworker install | https://assets.northerntool.com/products/577/documents/manuals/57703-2.pdf | Candidate edition; verify equipment applicability |
| Doosan DNM 5700 | https://www.doosan.com.ru/product/obrabatyvayushchiy-centr-doosan-dnm-5700 | Series brochure, not yet confirmed as service or LOTO manual |

## Required evidence chain

- Inventory asset ID, OEM/model, verified serial number and current installation/configuration retained in private source.
- OEM manual title, edition/revision, URL, acquisition date, license/distribution terms and SHA-256 if file lawfully retained.
- Manufacturer shutdown guidance separated from verified local isolation procedure.
- Authorized site employee independently verifies energy sources, isolator locations, stored energy, verification method and restart conditions before procedure approval.
- Never infer lock points from generic manuals, never use an emergency stop or control circuit as a substitute for energy isolation.
- Group equipment only after confirming comparable energy type/magnitude and isolation technique; record individual equipment coverage.
- OSHA 1910.147(c)(4) documentation exception applies only if all eight conditions are satisfied.

This is a research source register only. No manual PDFs have been uploaded or validated; no LOTO procedure has been approved. Future PM-Tracker integration should use a private document store with durable identifiers, hashes and access control, linked from equipment records.
