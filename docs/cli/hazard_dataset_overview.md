NSHM Hazard data is produced using PSHA sofware (usulaly `openquake` from GEM). This set of tools
let's us merge the results of mutltiple PSHA calcatluations add additional metadata so that the complete NSHM of derivates
are readily availble for further analysis use in tools ushc as the NHSM website.

Central to this is the concept of long term verificaiton and compararison between curves produced by differenjt products anbd 
or versions of the same product. There have been multiple revisions of the openquake software 3.16.0 - 3.22. over the three years
that hazard curves have been paroduced by the NSHM project.

To handle this at the meta dat level we have several metadata constructs:

 1. **HazardCurveProducerConfig** (HCPC) - captures the unique attributes that define some hazard curve production software/configuration. 
 2. **CompatibleHazardConfig** (CHC) - which provides a logical identifier for compatability accoss HCCs.
 3. The **calculation_id** attribute which is a unique identifier for the job that produced the curves. NSHM uses the AutomationTashID (from ToshiAPI)
    whcih lets us retrieve all the inputs required to reproduce those curves

Each Hazard Dataset includes these three ID attribue for each curve object, so that the provenance of the curve is preserved.
 