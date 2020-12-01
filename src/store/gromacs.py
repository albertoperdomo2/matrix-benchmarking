import common
import store

def rewrite_settings(params_dict):
    params_dict["machines"] = params_dict["Physical Nodes"]
    del params_dict["Physical Nodes"]
    del params_dict["MPI procs"]
    del params_dict["OMP threads/node"]

    platform = params_dict["platform"]
    if platform == "ocp":
        platform = "openshift"
        network = params_dict["network"]
        del params_dict["network"]
        platform = f"{platform}_{network}"
    elif platform == "bm":
        platform = "baremetal"
    params_dict["platform"] = platform

    if params_dict["isolated-infra"] == "---":
        params_dict["isolated-infra"] = "no"
    if params_dict["isolated-infra"] == "yes":
        params_dict["platform"] += "_isolated_infra"
    del params_dict["isolated-infra"]

    del params_dict["experiment"]

    if "network" in params_dict: del params_dict["network"]
    if "network" in all_keys: all_keys.remove("network")

    params_dict["@iteration"] = params_dict["iteration"]
    del params_dict["iteration"]


    return params_dict

all_keys = set()
def _populate_matrix(props_res_lst):
    for params_dict, result, location in props_res_lst:
        for k in all_keys:
            if k not in params_dict:
                params_dict[k] = "---"

        entry = store.add_to_matrix(params_dict, rewrite_settings, location)
        if not entry: return

        speed_result = result
        time_result = 1/speed_result

        entry.results.speed = speed_result
        entry.results.time = time_result

def parse_data(mode):
    props_res_lst = _parse_file(f"{common.RESULTS_PATH}/gromacs/results.csv")
    _populate_matrix(props_res_lst)

def _parse_file(filename):
    with open(filename) as record_f:
        lines = record_f.readlines()

    props_res_lst = []

    keys = []
    experiment_properties = {}

    for lineno, _line in enumerate(lines):
        if not _line.replace(',','').strip(): continue # ignore empty lines
        if _line.startswith("##") or _line.startswith('"##'): continue # ignore comments

        line_entries = _line.strip("\n,").split(",") # remove EOL and empty trailing cells

        if _line.startswith("#"):
            # line: # 1536k BM,platform: bm
            experiment_properties = {"experiment": line_entries.pop(0)[1:].strip()}
            for prop_value in line_entries:
                prop, found, value = prop_value.partition(":")
                if not found:
                    print("WARNING: invalid property for expe "
                          f"'{experiment_properties['experiment']}': '{prop_value}'")
                    continue
                experiment_properties[prop.strip()] = value.strip()
            continue

        if not keys:
            # line: 'Physical Nodes,MPI procs,OMP threads/node,Iterations'
            keys = [k for k in line_entries if k]
            continue

        # line: 1,1,4,0.569,0.57,0.57,0.57,0.569
        # props ^^^^^| ^^^^^^^^^^^^^^^^^^^^^^^^^ results

        line_properties = dict(zip(keys[:-1], line_entries))
        line_properties.update(experiment_properties)
        line_results = line_entries[len(keys)-1:]
        for ite, result in enumerate(line_results):
            props = dict(line_properties)
            props["iteration"] = ite
            try:
                float_result = float(result)
            except ValueError:
                if result:
                    print(f"ERROR: Failed to parse '{result}' for iteration #{ite} of", line_properties)
                continue
            props_res_lst.append((props, float_result, f"{filename}:{lineno} iteration#{ite}"))
            pass
        all_keys.update(props.keys())

    return props_res_lst
