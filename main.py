import pandas as pd
import sys
import os.path
import threading
import numpy as np
import re
import math
import csv
import datetime


p = 0.8         #(1-p) é la prioritá di ottimizzare i consumi, e p é la prioritá di ottimizzare i disservizi #[0.3, 0.5, 0.8]
teta = 0.1      #θ ∈ [0,1] è un tasso di apprendimento che rappresenta in che misura il nuovo prevale sui vecchi valori Q
gamma = 0.95    #γ ∈ [0,1] è un fattore di attualizzazione che indica l'importanza relativa dei premi futuri rispetto a quelli attuali
epsilon = 0.2   #epsilon é la probabilitá di scegliere un azione random. (1-epsilon) é la probabilitá di scegliere l'azione migliore
directory = datetime.datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
timestamp = ""
current_day = 0
current_hour = 0
count_row = 0
array_price = [0.0 for _ in range(24)]
loops = 1000            #loops = 100
one_memory = False      #one_memory = True


class Non_shiftable_load(object):

    def __init__(self, id, energy_demand = 0, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"):
        self.id = id
        self.energy_demand = energy_demand
        self.column_info = column_info
        self.working_hours = working_hours
        self.filename = os.path.join(directory, str(self.id)+".csv")
        self.initialize_file()
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time"])
        return

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            tmp = house_profile_DF.at[count_row, self.column_info]
            if tmp == -1:
                self.working_hours = "(-1)$"
                self.energy_demand = 0
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.energy_demand = tmp
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        if re.match(self.working_hours, str(current_hour)):
            E = self.energy_demand
            U = (1-p)*array_price[0]*E
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


class NSL_Battery(Non_shiftable_load):

    def __init__(self, id, max_capacity, current_state_of_charge = 0, energy_demand = 0, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"):
        Non_shiftable_load.__init__(self, id, energy_demand, column_info, working_hours)
        self.max_capacity = max_capacity
        self.current_state_of_charge = current_state_of_charge
        return
    
    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time", "output_state_of_charge"])
        return

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time, self.current_state_of_charge])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0, -1])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            tmp = house_profile_DF.at[count_row, self.column_info]
            if tmp == -1:
                self.working_hours = "(-1)$"
                self.current_state_of_charge = -1
            elif tmp == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.current_state_of_charge = tmp
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        if re.match(self.working_hours, str(current_hour)):
            E = min(self.energy_demand, self.max_capacity-self.current_state_of_charge)
            U = (1-p)*array_price[0]*E
            self.current_state_of_charge += E
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


def insert_NSL(device_list, path_dir_home):
    new_NSL = Non_shiftable_load("NSL_house.0", 0, "consumption_kwh")
    device_list.add(new_NSL)
    return


def insert_NSL_Battery(device_list, path_dir_home):
    battery_DF = pd.read_csv(os.path.join(path_dir_home, "NSLpev.csv"))
    row_index = 0
    while True:
        try:
            row = battery_DF.iloc[row_index]
        except IndexError:
            break
        max_capacity = float(row["battery_capacity_kwh"])
        energy_demand = float(row["charge_speed_kw"])
        new_NSL_Battery = NSL_Battery("NSL_Battery."+str(row_index), max_capacity, 0, energy_demand, "PEV_input_state_of_charge")
        device_list.add(new_NSL_Battery)
        row_index += 1
    return


class Shiftable_load(object):

    def __init__(self, id, k, Tne, state_number, energy_demand = 0, column_info = None, Tini = 0, Tend = 23, working_hours = "([0-9]|1[0-9]|2[0-3])$"):
        #Tne deve essere maggiore di zero e minore di 24 altrimenti sarebbe stato modellato come NSL
        #Tini, Tw, Tend devono rispettare i vincoli descritti nell'articolo e dovrebbero matchare con working_hours (e anche tutte le ore tra Tini e Tend devono matchare con working_hours)
        #l'attuale implementazione prevede una distanza tra Tini e Tend inferiore o uguale alle 24 ore (ad esempio Tini=0, Tend=23, Tne=24, e' un obj che deve assolutamente lavorare tutto il giorno)
        self.id = id
        self.k = k
        self.state_number = state_number
        self.Tne = Tne #numero di ore che l'oggetto deve restare in esecuzione per poter terminare
        self.Tini = Tini #prima ora del range disponibile
        self.Tw = -1 #utile nella funzione self.function
        self.Tend = Tend #ultima ora del range disponibile
        self.energy_demand = energy_demand
        self.column_info = column_info #colonne utili per fare l'update dei dati qualora l'implementazione lo preveda
        self.working_hours = working_hours
        self.hours_available = -1 #totale ore disponibili comprese tra tini/ora corrente e tend contenente tw e lunghe maggiore o uguale di tne
        self.hours_worked = -1
        #hours_worked e' il contatore delle ore che il device ha svolto (obiettivo: raggiungere le Tne ore di lavoro) 
        #se hours_worked == -1 non e' ancora stato definito
        #se hours_worked == 0 il device non e' ancora in funzione
        #se 0 < hours_worked < Tne il device e' in funzione
        #se hours_worked == Tne il device ha finito il suo lavoro e non e' piu' in funzione
        #hours_worked e' un dato che va letto al termine dell'ora corrente
        self.Q = np.zeros((24, self.state_number, 2), dtype=float)
        self.filename = os.path.join(directory, str(self.id)+".csv")
        self.initialize_file()
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time"])
        return

    def get_reward(self, index, Tw, kwh):
        value = (1-p)*array_price[index]*kwh + p*(self.k*(((Tw+24)-self.Tini)%24)) + 0.0000001
        return 1/value

    def get_state(self):
        return 0
    
    def next_state(self, state):
        return state

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            Tne = house_profile_DF.at[count_row, self.column_info[0]]
            hours_available = house_profile_DF.at[count_row, self.column_info[1]]
            #Tne deve essere minore o uguale a hours_of_work (si assume sempre che vengano sempre rispettati i vincoli del sistema)
            if Tne == -1:
                self.working_hours = "(-1)$"
                self.hours_worked = -1
            elif Tne == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.Tini = current_hour
                self.Tw = -1
                self.Tend = (current_hour+hours_available-1)%24
                self.hours_available = hours_available
                self.Tne = Tne
                self.hours_worked = -1
        return

    def chose_action(self, hour, state, Tw, hours_available, hours_worked, randomless=False):
        if hours_worked <= 0:                                       #se non e' attivo
            if hours_available == self.Tne:
                return 1, hour, hours_available-1, 1
            else:
                if randomless or np.random.random() >= epsilon:
                    bin_action = np.random.choice(np.where(self.Q[hour][state] == max(self.Q[hour][state]))[0], 1)[0]
                else:
                    bin_action = np.random.choice(2, 1)[0]
                if bin_action == 1:
                    return 1, hour, hours_available-1, 1
                else: #bin_action == 0
                    return 0, (hour+1)%24, hours_available-1, 0
        if hours_worked > 0 and hours_worked < self.Tne:            #se e' attivo
            return (1, Tw, hours_available-1, hours_worked+1)
        if hours_worked >= self.Tne:                                #se ha terminato
            return (0, self.Tini, hours_available-1, hours_worked)
        
    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        i = 1
        if re.match(self.working_hours, str(current_hour)): #caso in cui posso stare nelle righe diverse da -1
            if not one_memory:
                self.Q = np.zeros((24, self.state_number, 2), dtype=float)
            while i < loops:
                index = 0
                hour = current_hour
                state = self.get_state()
                Tw = self.Tw
                hours_available = self.hours_available
                hours_worked = self.hours_worked
                while hours_available > 0:
                    bin_action, new_Tw, new_hours_available, new_hours_worked = self.chose_action(hour, state, Tw, hours_available, hours_worked)
                    reward = self.get_reward(index, new_Tw, bin_action*self.energy_demand)
                    new_hour = (hour+1)%24
                    new_state = self.next_state(state)
                    self.Q[hour][state][bin_action] = self.Q[hour][state][bin_action]+teta*(reward+gamma*self.Q[new_hour][new_state][self.chose_action(new_hour, new_state, new_Tw, new_hours_available, new_hours_worked, True)[0]]-self.Q[hour][state][bin_action])
                    index += 1
                    hour = new_hour
                    state = new_state
                    Tw = new_Tw
                    hours_available = new_hours_available
                    hours_worked = new_hours_worked
                i += 1
            bin_action, self.Tw, self.hours_available, self.hours_worked = self.chose_action(current_hour, self.get_state(), self.Tw, self.hours_available, self.hours_worked, True)
            E = bin_action*self.energy_demand
            U = (1-p)*array_price[0]*E + p*(self.k*(((self.Tw+24)-self.Tini)%24))
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


class SL_Battery(Shiftable_load):

    def __init__(self, id, k, max_capacity, current_state_of_charge, Tne, state_number, energy_demand = 0, column_info = None, Tini = 0, Tend = 23, working_hours = "([0-9]|1[0-9]|2[0-3])$"): #Tini, Tw, Tend devono rispettare i vincoli descritti nell'articolo e dovrebbero matchare con working_hours
        Shiftable_load.__init__(self, id, k, Tne, state_number, energy_demand, column_info, Tini, Tend, working_hours)
        self.max_capacity = max_capacity
        self.current_state_of_charge = current_state_of_charge
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time", "output_state_of_charge"])
        return

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time, self.current_state_of_charge])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0, -1])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            new_state_of_charge = house_profile_DF.at[count_row, self.column_info[0]]
            hours_available = house_profile_DF.at[count_row, self.column_info[1]]
            #Tne deve essere minore o uguale a hours_of_work (si assume sempre che vengano sempre rispettati i vincoli del sistema)
            if new_state_of_charge == -1:
                self.working_hours = "(-1)$"
                self.hours_worked = -1
            elif new_state_of_charge == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.Tini = current_hour
                self.Tw = -1
                self.Tend = (current_hour+hours_available-1)%24
                self.hours_available = hours_available
                self.current_state_of_charge = new_state_of_charge
                self.Tne = min(self.hours_available, math.ceil((self.max_capacity-self.current_state_of_charge)/self.energy_demand))
                self.hours_worked = -1
        return

    def get_state(self, state_of_charge):
        state = 0
        if self.state_number == 1: return state
        delta = self.max_capacity/(self.state_number-1)
        if state_of_charge == self.max_capacity:
            state = self.state_number-1
        else:
            for i in range(self.state_number-1):
                if delta*i <= state_of_charge < delta*(i+1):
                    state = i
                    break
        return state

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        i = 1
        if re.match(self.working_hours, str(current_hour)): #caso in cui posso stare nelle righe diverse da -1
            if not one_memory:
                self.Q = np.zeros((24, self.state_number, 2), dtype=float)
            while i < loops:
                index = 0
                hour = current_hour
                state = self.get_state(self.current_state_of_charge)
                Tw = self.Tw
                hours_available = self.hours_available
                hours_worked = self.hours_worked
                state_of_charge = self.current_state_of_charge
                while hours_available > 0:
                    bin_action, new_Tw, new_hours_available, new_hours_worked = self.chose_action(hour, state, Tw, hours_available, hours_worked)
                    kwh = min(self.max_capacity-state_of_charge, bin_action*self.energy_demand)
                    new_state_of_charge = state_of_charge + kwh
                    reward = self.get_reward(index, new_Tw, kwh)
                    new_hour = (hour+1)%24
                    new_state = self.get_state(new_state_of_charge)
                    self.Q[hour][state][bin_action] = self.Q[hour][state][bin_action]+teta*(reward+gamma*self.Q[new_hour][new_state][self.chose_action(new_hour, new_state, new_Tw, new_hours_available, new_hours_worked, True)[0]]-self.Q[hour][state][bin_action])
                    index += 1
                    hour = new_hour
                    state = new_state
                    Tw = new_Tw
                    hours_available = new_hours_available
                    hours_worked = new_hours_worked
                    state_of_charge = new_state_of_charge
                i += 1
            bin_action, self.Tw, self.hours_available, self.hours_worked = self.chose_action(current_hour, self.get_state(self.current_state_of_charge), self.Tw, self.hours_available, self.hours_worked, True)
            E = min(self.max_capacity-self.current_state_of_charge, bin_action*self.energy_demand)
            U = (1-p)*array_price[0]*E + p*(self.k*(((self.Tw+24)-self.Tini)%24))
            self.current_state_of_charge += E
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


def insert_SL(device_list, path_dir_home):
    return


def insert_SL_Battery(device_list, path_dir_home):
    battery_DF = pd.read_csv(os.path.join(path_dir_home, "SLpev.csv"))
    row_index = 0
    while True:
        try:
            row = battery_DF.iloc[row_index]
        except IndexError:
            break
        k = float(row["k"])
        max_capacity = float(row["battery_capacity_kwh"])
        state_number = int(row["state_number"])
        energy_demand = float(row["charge_speed_kw"])
        new_battery = SL_Battery("SL_Battery."+str(row_index), k, max_capacity, 0, 0, state_number, energy_demand, ("PEV_input_state_of_charge", "PEV_hours_of_charge"))
        device_list.add(new_battery)
        row_index += 1
    return


class Naif_Battery(object):

    def __init__(self, id, max_capacity, current_state_of_charge, deficit = 0, energy_demand = 0, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"): #Tini, Tw, Tend devono rispettare i vincoli descritti nell'articolo e dovrebbero matchare con working_hours
        self.id = id
        self.max_capacity = max_capacity
        self.current_state_of_charge = current_state_of_charge
        self.deficit = deficit
        self.energy_demand = energy_demand
        self.column_info = column_info
        self.working_hours = working_hours
        self.hours_available = -1 #totale ore disponibili comprese tra tini/ora corrente e tend contenente tw e lunghe maggiore o uguale di tne
        self.filename = os.path.join(directory, str(self.id)+".csv")
        self.initialize_file()
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            new_state_of_charge = house_profile_DF.at[count_row, self.column_info[0]]
            hours_available = house_profile_DF.at[count_row, self.column_info[1]]
            if new_state_of_charge == -1:
                self.working_hours = "(-1)$"
            elif new_state_of_charge == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.hours_available = hours_available
                self.current_state_of_charge = new_state_of_charge
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time", "output_state_of_charge"])
        return

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time, self.current_state_of_charge])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0, -1])
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        if re.match(self.working_hours, str(current_hour)):
            current_kwh = 0.0
            state_of_charge = min(self.max_capacity, self.current_state_of_charge + self.deficit)
            d = {(array_price[index], index) : 0.0 for index in range(self.hours_available)}
            for k in sorted(list(d.keys())):
                kwh = min(self.energy_demand, self.max_capacity-state_of_charge)
                d[k] = kwh
                state_of_charge += kwh
                if k[1] == 0:
                    current_kwh = kwh
            E = current_kwh
            U = (1-p)*array_price[0]*E
            self.current_state_of_charge += E
            self.hours_available -= 1
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


def insert_Naif_Battery(device_list, path_dir_home):
    battery_DF = pd.read_csv(os.path.join(path_dir_home, "Naifpev.csv"))
    row_index = 0
    while True:
        try:
            row = battery_DF.iloc[row_index]
        except IndexError:
            break
        energy_demand = float(row["charge_speed_kw"])
        deficit = float(row["deficit"])
        max_capacity = float(row["battery_capacity_kwh"])
        new_battery = Naif_Battery("Naif_Battery."+str(row_index), max_capacity, 0, deficit, energy_demand, ("PEV_input_state_of_charge","PEV_hours_of_charge"))
        device_list.add(new_battery)
        row_index += 1
    return
    return


class Controlable_load(object):

    def __init__(self, id, beta, min_energy_demand, max_energy_demand, state_number, action_number, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"): #si assume che action_number >=2
        self.id = id
        self.beta = beta
        self.min_energy_demand = min_energy_demand #si assuma sia diverso da max_energy_demand
        self.max_energy_demand = max_energy_demand #si assuma sia diverso da min_energy_demand
        self.state_number = state_number
        self.action_number = action_number
        self.column_info = column_info
        self.working_hours = working_hours
        self.action_list = self.initialize_action_list() #min e max energy demand ci sono sempre per costruzione
        self.Q = np.zeros((24, self.state_number, self.action_number), dtype=float)
        self.filename = os.path.join(directory, str(self.id)+".csv")
        self.initialize_file()
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time"])
        return

    def initialize_action_list(self):
        delta_grid = (self.max_energy_demand-self.min_energy_demand)/(self.action_number-1)
        action_list = []
        for i in range(self.action_number):
            action_list.append(self.min_energy_demand+(delta_grid*i))
        action_list.append(self.max_energy_demand)
        return action_list

    def chose_action(self, hour, state, randomless=False):
        if randomless or np.random.random() >= epsilon:
            action = np.random.choice(np.where(self.Q[hour][state] == max(self.Q[hour][state]))[0], 1)[0]
        else:
            action = np.random.choice(self.action_number, 1)[0]
        return action

    def get_reward(self, index, kwh):
        value = (1-p)*array_price[index]*kwh+p*(self.beta*((kwh-self.max_energy_demand)**2)) + 0.0000001
        return 1/value

    def get_state(self):
        return 0

    def next_state(self, state):
        return state

    def is_final_state(self, state):
        return False

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            tmp = house_profile_DF.at[count_row, self.column_info]
            if tmp == -1:
                self.working_hours = "(-1)$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        i = 1
        if re.match(self.working_hours, str(current_hour)): #caso in cui posso stare nelle righe diverse da -1
            if not one_memory:
                self.Q = np.zeros((24, self.state_number, self.action_number), dtype=float)
            while i < loops:
                index = 0
                hour = current_hour
                state = self.get_state()
                while index < 24  and not self.is_final_state(state):
                    action = self.chose_action(hour)
                    reward = self.get_reward(index, self.action_list[action])
                    new_hour = (hour+1)%24
                    new_state = self.next_state(state)
                    self.Q[hour][state][action] = self.Q[hour][state][action]+teta*(reward+gamma*self.Q[new_hour][new_state][self.chose_action(new_hour, new_state, True)[0]]-self.Q[hour][state][action])
                    index += 1
                    hour = new_hour
                    state = new_state
                i += 1
            action = self.chose_action(current_hour, self.get_state(), True)
            E = self.action_list[action]
            U = (1-p)*array_price[0]*E+p*(self.beta*((E-self.max_energy_demand)**2))
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


class CL_Battery(Controlable_load):

    def __init__(self, id, beta, min_energy_demand, max_energy_demand, state_number, action_number, max_capacity, current_state_of_charge = 0, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"):
        Controlable_load.__init__(self, id, beta, min_energy_demand, max_energy_demand, state_number, action_number, column_info, working_hours)
        self.max_capacity = max_capacity
        self.current_state_of_charge = current_state_of_charge
        return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time", "output_state_of_charge"])
        return

    def get_min_max_index_action(self, state_of_charge):
        min_action = -1 #forse meglio inizializzare a -1 perche' nel caso in cui non sia possibili effettuare nessuna azione e non vi sia l'azione che carica 0 kwh verrebbe effettuata l'azione all'indice 0 che e' un'azione invalida siccome siamo nel caso in cui nessuna azione e' possibile. con l'inizzializzazione a -1, nel caso descritto dovrebbe avvenite un errore
        max_action = self.action_number-1
        check = False
        for i, action in enumerate(self.action_list):
            if not check and state_of_charge+action >= 0 and state_of_charge+action <= self.max_capacity:
                check = True
                min_action = i
                max_action = i
            if check and state_of_charge+action >= 0 and state_of_charge+action <= self.max_capacity:
                max_action = i
        return (min_action, max_action)

    def get_state(self, state_of_charge):
        state = 0
        if self.state_number == 1: return state
        delta = self.max_capacity/(self.state_number-1)
        if state_of_charge == self.max_capacity:
            state = self.state_number-1
        else:
            for i in range(self.state_number-1):
                if delta*i <= state_of_charge < delta*(i+1):
                    state = i
                    break
        return state

    def get_reward(self, index, kwh, max_energy_demand):
        value = (1-p)*array_price[index]*kwh+p*(self.beta*((kwh-max_energy_demand)**2)) + 0.0000001
        return 1/value
        
    def chose_action(self, hour, state, state_of_charge, randomless=False):
        min_action, max_action = self.get_min_max_index_action(state_of_charge)
        if randomless or np.random.random() >= epsilon:
            action = min_action+np.random.choice(np.where(self.Q[hour][state][min_action:max_action+1] == max(self.Q[hour][state][min_action:max_action+1]))[0], 1)[0]
        else:
            action = min_action+np.random.choice(len(self.Q[hour][state][min_action:max_action+1]), 1)[0]
        return action

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time, self.current_state_of_charge])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0, -1])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            new_current_state_of_charge = house_profile_DF.at[count_row, self.column_info]
            if new_current_state_of_charge == -1:
                self.working_hours = "(-1)$"
                self.current_state_of_charge = -1
            elif new_current_state_of_charge == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.current_state_of_charge = new_current_state_of_charge
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        i = 1
        t = 1
        if re.match(self.working_hours, str(current_hour)):
            if not one_memory:
                self.Q = np.zeros((24, self.state_number, self.action_number), dtype=float)
            while i < loops:
                index = 0
                hour = current_hour
                state = self.get_state(self.current_state_of_charge)
                state_of_charge = self.current_state_of_charge
                while state_of_charge != self.max_capacity and index < 24:
                    action = self.chose_action(hour, state, state_of_charge)
                    kwh = self.action_list[action]
                    if kwh == 0:
                        if state_of_charge+self.action_list[action+1] > self.max_capacity: #niente index out of range per costruzione
                            kwh = min(self.max_energy_demand, self.max_capacity-state_of_charge) #a causa di un'assenza di totale liberta' di range, quando la action genera kwh == 0 allora "rabbocco" kwh al current_max_energy_demand
                    local_max_energy_demand = min(self.max_energy_demand, self.max_capacity-state_of_charge)
                    reward = self.get_reward(index, kwh, local_max_energy_demand)
                    new_state_of_charge = state_of_charge + kwh
                    new_hour = (hour+1)%24
                    new_state = self.get_state(new_state_of_charge)
                    self.Q[hour][state][action] = self.Q[hour][state][action]+teta*(reward+gamma*self.Q[new_hour][new_state][self.chose_action(new_hour, new_state, new_state_of_charge, True)]-self.Q[hour][state][action])
                    hour = new_hour
                    state = new_state
                    state_of_charge = new_state_of_charge
                    t += 1
                    index += 1
                i += 1
            action = self.chose_action(current_hour, self.get_state(self.current_state_of_charge), self.current_state_of_charge, True)
            E = self.action_list[action]
            if E == 0:
                if self.current_state_of_charge+self.action_list[action+1] > self.max_capacity: #niente index out of range per costruzione
                    E = min(self.max_energy_demand, self.max_capacity-self.current_state_of_charge) #a causa di un'assenza di totale liberta' di range, quando la action genera E == 0 allora "rabbocco" E al current_max_energy_demand
            local_max_energy_demand = min(self.max_energy_demand, self.max_capacity-self.current_state_of_charge)
            U = (1-p)*array_price[0]*E+p*(self.beta*((E-local_max_energy_demand)**2))
            self.current_state_of_charge += E
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U


def insert_CL(device_list, path_dir_home):

    return


def insert_CL_Battery(device_list, path_dir_home):
    battery_DF = pd.read_csv(os.path.join(path_dir_home, "CLpev.csv"))
    row_index = 0
    while True:
        try:
            row = battery_DF.iloc[row_index]
        except IndexError:
            break
        max_energy_demand = float(row["charge_speed_kw"])
        min_energy_demand = 0 #-float(row["discharge_speed_kw"]) #attualmente l'algoritmo non e' pensato per device che producono energia (va rivista la formula delle reward, e forse anche la formula di U, ma penso sono la prima)
        action_number = int(row["action_number"])
        state_number = int(row["state_number"])
        beta = float(row["beta"])
        max_capacity = float(row["battery_capacity_kwh"])
        new_battery = CL_Battery("CL_Battery."+str(row_index), beta, min_energy_demand, max_energy_demand, state_number, action_number, max_capacity, 0, "PEV_input_state_of_charge")
        device_list.add(new_battery)
        row_index += 1
    return


class DP_Battery(object):

    class Info(object):
        def __init__(self, value = 0.0, first_action = -1):
            self.value = value
            self.first_action = first_action
        def clone(self, info_obj):
            self.value = info_obj.value
            self.first_action = info_obj.first_action

    def __init__(self, id, beta, current_state_of_charge, max_capacity, min_energy_demand, max_energy_demand, action_number, state_number, column_info = None, working_hours = "([0-9]|1[0-9]|2[0-3])$"): #si assume che action_number >=2
            self.id = id
            self.beta = beta
            self.current_state_of_charge = current_state_of_charge
            self.max_capacity = max_capacity
            self.min_energy_demand = min_energy_demand #si assuma sia diverso da max_energy_demand
            self.max_energy_demand = max_energy_demand #si assuma sia diverso da min_energy_demand
            self.action_number = action_number
            self.state_number = state_number
            self.column_info = column_info
            self.working_hours = working_hours
            self.action_list = self.initialize_action_list(action_number) #min e max energy demand ci sono sempre per costruzione
            self.filename = os.path.join(directory, str(self.id)+".csv")
            self.initialize_file()
            self.hours_of_charge = 0
            return

    def initialize_file(self):
        with open(self.filename, "w") as file_object:
            csv.writer(file_object).writerow(["timestamp", "on/off", "E", "U", "time", "output_state_of_charge"])
        return

    def initialize_action_list(self, action_number):
        delta_grid = (self.max_energy_demand-self.min_energy_demand)/(action_number-1)
        action_list = []
        for i in range(0,action_number-1):
            action_list.append(self.min_energy_demand+(delta_grid*i))
        action_list.append(self.max_energy_demand)
        return action_list

    def get_min_max_index_action(self, state_of_charge, max_capacity):
        min_action = -1
        max_action = -1
        check = False
        for i, action in enumerate(self.action_list):
            if not check and state_of_charge+action >= 0 and state_of_charge+action <= max_capacity:
                check = True
                min_action = i
                max_action = i
            if check and state_of_charge+action >= 0 and state_of_charge+action <= max_capacity:
                max_action = i
        return (min_action, max_action)

    def charge_to_state(self, state_of_charge):
        state = 0
        delta = self.max_capacity/(self.state_number-1)
        if state_of_charge != 0.0:
            for i in range(self.state_number-1):
                state = i
                if delta*i < state_of_charge <= delta*(i+1):
                    break
        return state

    def state_to_charge(self, state):
        return state*(self.max_capacity/(self.state_number-1))

    def get_reward(self, index, kwh, max_energy_demand):
        value = (1-p)*array_price[index]*kwh+p*(self.beta*((kwh-max_energy_demand)**2)) +0.00000001
        return 1/value

    def update_history(self, E, U, time):
        with open(self.filename, "a") as file_object:
            if re.match(self.working_hours, str(current_hour)):
                csv.writer(file_object).writerow([timestamp, "on", E, U, time, self.current_state_of_charge])
            else:
                csv.writer(file_object).writerow([timestamp, "off", 0, 0, 0, -1])
        return

    def update_data(self, house_profile_DF):
        if self.column_info != None:
            input_state_of_charge = house_profile_DF.at[count_row, self.column_info[0]]
            hours_of_charge = house_profile_DF.at[count_row, self.column_info[1]]
            if input_state_of_charge == -1:
                self.working_hours = "(-1)$"
                self.current_state_of_charge = -1
            elif input_state_of_charge == -2:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.hours_of_charge -= 1
            else:
                self.working_hours = "([0-9]|1[0-9]|2[0-3])$"
                self.current_state_of_charge = input_state_of_charge
                self.hours_of_charge = hours_of_charge
        return

    def function(self):
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        if re.match(self.working_hours, str(current_hour)):
            tmp_info = self.Info()
            action_zero = self.action_list.index(0.0)
            len_x = self.hours_of_charge+1
            len_y = self.charge_to_state(self.max_capacity-self.current_state_of_charge)+1
            Q = [[self.Info() for _ in range(len_x)] for _ in range(len_y)]
            
            for state in range(1, len_y):
                state_of_charge = self.current_state_of_charge
                local_max_capacity = self.current_state_of_charge+self.state_to_charge(state)

                for hour in range(1, len_x):
                    min_index, max_index = self.get_min_max_index_action(state_of_charge, local_max_capacity)
                    best_action = action_zero

                    for action in range(min_index, max_index+1):
                        kwh = self.action_list[action]
                        if kwh == 0:
                            if state_of_charge+self.action_list[action+1] > local_max_capacity: #niente index out of range per costruzione
                                kwh = min(self.max_energy_demand, local_max_capacity-state_of_charge) #a causa di un'assenza di totale liberta' di range, quando la action genera kwh == 0 allora "rabbocco" kwh al current_max_energy_demand
                        tmp_info.clone(Q[self.charge_to_state(self.max_capacity-(state_of_charge+kwh))][hour-1])
                        tmp_info.value += self.get_reward(hour-1, kwh, local_max_capacity-state_of_charge)
                        if tmp_info.first_action == -1:
                            tmp_info.first_action = action
                        if tmp_info.value > Q[state][hour].value:
                            Q[state][hour].clone(tmp_info)
                            best_action = action
                    state_of_charge += self.action_list[best_action]
            if len_y != 1:
                action = Q[len_y-1][len_x-1].first_action
            else:
                action = action_zero
            E = self.action_list[action]
            if E == 0:
                if self.current_state_of_charge+self.action_list[action+1] > self.max_capacity: #niente index out of range per costruzione
                    E = min(self.max_energy_demand, self.max_capacity-self.current_state_of_charge) #a causa di un'assenza di totale liberta' di range, quando la action genera kwh == 0 allora "rabbocco" kwh al current_max_energy_demand
            U = (1-p)*array_price[0]*E+p*(self.beta*((E-self.max_energy_demand)**2))
            self.current_state_of_charge += E
        time = datetime.datetime.now()-time
        self.update_history(E, U, time)
        return E, U 


def insert_DP_Battery(device_list, path_dir_home):
    battery_DF = pd.read_csv(os.path.join(path_dir_home, "DPpev.csv"))
    row_index = 0
    while True:
        try:
            row = battery_DF.iloc[row_index]
        except IndexError:
            break
        max_energy_demand = float(row["charge_speed_kw"])
        min_energy_demand = 0 #-float(row["discharge_speed_kw"]) #attualmente l'algoritmo non e' pensato per device che producono energia (va rivista la formula delle reward, e forse anche la formula di U, ma penso sono la prima)
        action_number = int(row["action_number"])
        state_number = int(row["state_number"])
        beta = float(row["beta"])
        max_capacity = float(row["battery_capacity_kwh"])
        new_battery = DP_Battery("DP_Battery."+str(row_index), beta, 0, max_capacity, min_energy_demand, max_energy_demand, action_number, state_number, ("PEV_input_state_of_charge","PEV_hours_of_charge"))
        device_list.add(new_battery)
        row_index += 1
    return


class Device_thread(threading.Thread):

    def __init__(self, device):
        threading.Thread.__init__(self)
        self.device = device
        self.E = None
        self.U = None
        return

    def run(self):
        E, U = self.device.function()
        self.E = E
        self.U = U
        return

    def join(self):
        threading.Thread.join(self)
        return self.E, self.U


def get_input(argv):
    try:
        path_dir_home = argv[1]
        if not os.path.isdir(path_dir_home):
            print("error arguments: <path_dir_home>")
            return None
    except IndexError:
         print("missing arguments: <path_dir_home>")
         return None
    return path_dir_home


def insert_devices(device_list, path_dir_home):
    #insert_NSL(device_list, path_dir_home)
    #insert_NSL_Battery(device_list, path_dir_home)
    #insert_SL_Battery(device_list, path_dir_home)
    #insert_Naif_Battery(device_list, path_dir_home)
    insert_CL_Battery(device_list, path_dir_home)
    #insert_DP_Battery(device_list, path_dir_home)
    return


def main():
#si assume che i dispositivi nella casa non possono variare al variare dei giorni
    global timestamp
    global current_day
    global current_hour
    global count_row
    global array_price
    global loops
    global one_memory
    os.mkdir(directory)
    path_dir_home = get_input(sys.argv)
    if path_dir_home == None: return
    device_list = set()
    insert_devices(device_list, path_dir_home)
    house_profile_DF = pd.read_csv(os.path.join(path_dir_home, "newprofiles.csv"))
    filename_main = os.path.join(directory, "main.csv")
    with open(filename_main, "w") as file_object:
        csv.writer(file_object).writerow(["timestamp", "E", "U", "time"])
    while True:
        time = datetime.datetime.now()
        E = 0.0
        U = 0.0
        try:
            timestamp = house_profile_DF.at[count_row, "timestamp"]
            for i in range(24):
                array_price[i] = house_profile_DF.at[count_row+i, "energy_market_price"]
        except:
            break
        thread_list = []
        for device in device_list:
            device.update_data(house_profile_DF)
            thread = Device_thread(device)
            thread_list.append(thread)
            thread.start()
        for thread in thread_list:
            e, u = thread.join()
            E += e
            U += u
        time = datetime.datetime.now()-time
        with open(filename_main, "a") as file_object:
            csv.writer(file_object).writerow([timestamp, E, U, time])
        current_hour += 1
        if current_hour == 24:
            current_day += 1
            current_hour = 0
        count_row += 1
    file_name = os.path.join(directory, "info.txt")
    with open(file_name, "w") as file_object:
        file_object.write("p: {} (p ∈ [0,1] é la prioritá di ottimizzare i disservizi. (1-p) é la prioritá di ottimizzare i consumi. Nell'articolo é [0.8, 0.5, 0.3])\n".format(p))
        file_object.write("teta: {} (θ ∈ [0,1] è un tasso di apprendimento che rappresenta in che misura il nuovo prevale sui vecchi valori Q. Nell'articolo é 0.1)\n".format(teta))
        file_object.write("gamma: {} (γ ∈ [0,1] è un fattore di attualizzazione che indica l'importanza relativa dei premi futuri rispetto a quelli attuali. Nell'articolo é 0.95)\n".format(gamma))
        file_object.write("epsilon: {} (epsilon é la probabilitá di scegliere un azione random. (1-epsilon) é la probabilitá di scegliere l'azione migliore)\n".format(epsilon))
        file_object.write("one_memory: {}\n".format(one_memory))
        file_object.write("loops: {}\n".format(loops))
    return


if __name__ == "__main__":
    main()
