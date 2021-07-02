import pandas as pd
import sys
import os.path
import csv

def get_input(argv):
    try:
        path_dir_home = argv[1]
        path_dir_tests = argv[2]
        NSL_file = argv[3]
        if not os.path.isdir(path_dir_home) or not os.path.isdir(path_dir_tests) or not os.path.isfile(NSL_file):
            print("error arguments: <path_dir_home> <path_dir_tests> <NSL_file>")
            return None
    except IndexError:
         print("missing arguments: <path_dir_home> <path_dir_tests> <NSL_file>")
         return None
    return (path_dir_home, path_dir_tests, NSL_file)


def main():
    p = 0.3
    result = get_input(sys.argv)
    if result == None: return
    path_dir_home, path_dir_tests, NSL_file = result
    house_profile_DF = pd.read_csv(os.path.join(path_dir_home, "newprofiles.csv"))
    NSL_file_DF = pd.read_csv(NSL_file)
    d = dict()

    for device_file in os.listdir(path_dir_tests):
        if device_file == "main.csv" or device_file == "info.txt" or device_file == "tabella.csv" or device_file[0] == ".": continue
        file_DF = pd.read_csv(os.path.join(path_dir_tests, device_file))
        i = 0
        info1 = {"tot_costo": 0, "tot_kw": 0, "tot_stato_finale": 0}
        info2 = {"tot_costo": 0, "tot_kw": 0, "tot_stato_finale": 0}
        count_plug_in = 0
        count_hours_plugin = 0
        stato_finale1 = 0
        stato_finale2 = 0
        while True:
            try:
                future_price = house_profile_DF.at[i, "energy_market_price"]
                E1 = file_DF.at[i, "E"]
                new_stato_finale1 = file_DF.at[i, "output_state_of_charge"]
                E2 = NSL_file_DF.at[i, "E"]
                new_stato_finale2 = NSL_file_DF.at[i, "output_state_of_charge"]
                x = house_profile_DF.at[i, "PEV_input_state_of_charge"]
            except:
                break
            if x >= 0:
                info1["tot_stato_finale"] += stato_finale1
                info2["tot_stato_finale"] += stato_finale2
                count_plug_in += 1
            if x != -1:
                stato_finale1 = new_stato_finale1
                stato_finale2 = new_stato_finale2
                info1["tot_costo"] += E1*future_price
                info2["tot_costo"] += E2*future_price
                info1["tot_kw"] += E1
                info2["tot_kw"] += E2
                count_hours_plugin += 1
            i += 1
        info1["tot_stato_finale"] += stato_finale1
        info2["tot_stato_finale"] += stato_finale2


        
        d[device_file] =    {
                                "costo" : (info1["tot_costo"], 100-((info1["tot_costo"]*100)/info2["tot_costo"])),
                                "kw" : (info1["tot_kw"], 100-((info1["tot_kw"]*100)/info2["tot_kw"])),
                                "stato_finale_M" : (info1["tot_stato_finale"]/count_plug_in, 100-((info1["tot_stato_finale"]*100)/info2["tot_stato_finale"])),
                                "prezzo_M_carico" : (info1["tot_costo"]/info1["tot_kw"], 100-(((info1["tot_costo"]/info1["tot_kw"])*100)/(info2["tot_costo"]/info2["tot_kw"])))
                            }
        d[device_file]["punteggio"] = (1-p)*(d[device_file]["costo"][1]+d[device_file]["prezzo_M_carico"][1])-p*(d[device_file]["kw"][1]+d[device_file]["stato_finale_M"][1])
        
    stampa = []
    for k, v in d.items():
        stampa.append((d[k]["punteggio"], k, v))
    for x in reversed(sorted(stampa)):
        print(x[1])
        for k, v in d[x[1]].items():
            print(k, v)
        print()
    
main()
