import pandas as pd
import sys
import os.path
import csv

def get_input(argv):
    try:
        path_dir_home = argv[1]
        file1 = argv[2]
        file2 = argv[3]
        if not os.path.isdir(path_dir_home) or not os.path.isfile(file1) or not os.path.isfile(file2):
            print("error arguments: <path_dir_home> <file1.csv> <NSL_file2.csv>")
            return None
    except IndexError:
         print("missing arguments: <path_dir_home> <file1.csv> <NSL_file2.csv>")
         return None
    return (path_dir_home, file1, file2)

def main():
    result = get_input(sys.argv)
    if result == None: return
    path_dir_home, file1, file2 = result
    house_profile_DF = pd.read_csv(os.path.join(path_dir_home, "newprofiles.csv"))
    file1_DF = pd.read_csv(file1)
    file2_DF = pd.read_csv(file2)
    i = 0
    tot1 = 0.0
    tot2 = 0.0
    count1 = 0
    count2 = 0
    count = 0
    totprice = 0.0
    while True:
        try:
            future_price = house_profile_DF.at[i, "energy_market_price"]
            E1 = file1_DF.at[i, "E"]
            E2 = file2_DF.at[i, "E"]
            x = house_profile_DF.at[i, "PEV_input_state_of_charge"]
        except:
            break
        if E1 != 0:
            tot1 += E1*future_price
            count1 += E1
        if E2 != 0:
            tot2 += E2*future_price
            count2 += E2
        if x != -1:
            totprice += future_price
            count += 1
        i += 1


    print(tot1/count1, tot1, count1)
    print(tot2/count2, tot2, count2)
    print(totprice/count, totprice, count)

main()
