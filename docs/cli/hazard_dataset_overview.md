NSHM Hazard data is produced using PSHA software (usually `openquake` from GEM). This set of tools
lets us merge the results of multiple PSHA calculations and add additional metadata so that the complete NSHM datasets are
readily available for further analysis and use in tools such as the NSHM website.

Central to this is the concept of long term verification and comparison between curves produced by different products and
versions of the same product. There have been multiple revisions of the openquake software 3.16.0 - 3.22. over the three years
that hazard curves have been produced by the NSHM project.

To handle this at the metadata level we have several metadata constructs:

1. **HazardCurveProducerConfig** (HCPC) - captures the unique attributes that define some hazard curve production software/configuration.
2. **CompatibleHazardConfig** (CHC) - which provides a logical identifier for compatibility across HCPCs.
3. The **calculation_id** attribute which is a unique identifier for the job that produced the curves. NSHM uses the AutomationTaskID (from ToshiAPI)
   which lets us retrieve all the inputs required to reproduce those curves.

Each Hazard Dataset includes these three ID attributes for each curve object, so that the provenance of the curve is preserved.