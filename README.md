# Home Energy Management System with Reinforcement Learning

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Research](https://img.shields.io/badge/research-bachelor%20thesis-orange.svg)](https://github.com/VincenzoImp/bachelor-degree-thesis)

> An intelligent Home Energy Management System (HEMS) that uses Artificial Neural Networks and Multi-Agent Reinforcement Learning to optimize electric vehicle charging and household energy consumption.

## 🎯 Overview

This project implements and evaluates four different models for integrating Plug-in Electric Vehicle (PEV) battery management into a smart home energy system. The system combines:

- **Artificial Neural Networks (ANN)** for electricity price prediction
- **Multi-Agent Reinforcement Learning (MARL)** for optimal decision making
- **Real-world data integration** from Nordic electricity markets and EV usage patterns

## 🚗 Problem Statement

Electric vehicles are becoming increasingly popular, but their charging patterns can significantly impact household energy costs and grid stability. This project addresses:

- **Peak demand issues** when EVs charge simultaneously after work hours
- **High electricity costs** during peak pricing periods
- **Grid stability concerns** from uncoordinated charging
- **User convenience** vs. energy cost optimization trade-offs

## 🧠 Technical Approach

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Price Data    │───▶│  Neural Network  │───▶│ Price Prediction│
│   (Nord Pool)   │    │   (18 inputs)    │    │   (24h ahead)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Device Agents  │◀───│      HEMS        │◀───│  Q-Learning     │
│ (EV, HVAC, etc.)│    │   Coordinator    │    │   Optimizer     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Core Components

1. **Price Prediction Module** (`ANN`)
   - 18 input features (time, weather, historical prices)
   - Sigmoid activation function
   - Levenberg-Marquardt training algorithm

2. **Multi-Agent Decision System** (`MARL`)
   - Independent Q-learning agents for each device
   - ε-greedy exploration strategy
   - Distributed optimization approach

3. **Battery Management Models** (4 implementations)
   - Non-Shiftable, Shiftable, Naïf, and Controllable approaches

## 📊 Models Implemented

### 1. Non-Shiftable Battery (`NSL_Battery`)
**Baseline model** - Charges immediately when plugged in
- ✅ Simple implementation
- ❌ No cost optimization
- 🎯 Reference point for comparisons

### 2. Shiftable Battery (`SL_Battery`) 
**Time-shifting model** - Delays charging to optimal windows
- ✅ Significant cost savings (up to 1.99% improvement)
- ✅ Reduces peak demand
- ❌ Must charge continuously once started
- 🔧 Parameters: `k` (inconvenience cost), `Tne` (charging duration)

### 3. Naïf Battery (`Naif_Battery`)
**Greedy optimization** - Charges during cheapest available hours
- ✅ Best overall performance (up to 16.89% improvement)
- ✅ Can split charging across multiple periods
- ✅ Simple yet effective algorithm
- 🔧 Parameters: `deficit` (charge level target)

### 4. Controllable Battery (`CL_Battery`)
**Continuous optimization** - Adjusts charging power dynamically
- ✅ Maximum flexibility (up to 3.43% improvement)
- ✅ Real-time adaptation
- ❌ Most complex implementation
- 🔧 Parameters: `β` (satisfaction cost), `action_number` (power levels)

## 📈 Performance Results

### Scenario Analysis

The system was evaluated across three scenarios with different user priorities:

| Scenario | Cost Focus | Comfort Focus | Best Model | Improvement |
|----------|------------|---------------|------------|-------------|
| ρ = 0.3  | 70%        | 30%          | Naïf_Battery.2 | 16.89% |
| ρ = 0.5  | 50%        | 50%          | Naïf_Battery.0 | 10.76% |
| ρ = 0.8  | 20%        | 80%          | Naïf_Battery.0 | 4.30% |

### Key Findings

- **Naïf Battery models** consistently outperformed complex RL approaches
- **Flexibility beats optimization** - ability to split charging sessions was crucial
- **Context matters** - optimal strategy depends on user priorities
- **Diminishing returns** - simple heuristics often sufficient

## 📁 Project Structure

```
bachelor-degree-thesis/
├── main.py                 # Main HEMS simulation engine
├── get_newprofile.py      # Data preprocessing script
├── show_results.py        # Results analysis and visualization
├── comparison.py          # Model comparison utilities
├── latex/                 # Thesis documentation (LaTeX)
│   └── main.tex
├── data/                  # Sample datasets
│   ├── energy_prices.csv
│   ├── pev_usage.csv
│   └── home_profiles.csv
└── README.md
```

## 🔧 Implementation Details

### Device Classes

Each battery model inherits from base classes with specific behaviors:

```python
class SL_Battery(Shiftable_load):
    def function(self):
        # Q-learning training loop
        for episode in range(loops):
            # Simulate charging scenarios
            # Update Q-table based on rewards
        
        # Execute optimal action
        return energy_consumed, utility_cost
```

### Q-Learning Implementation

```python
# Q-value update rule
Q[state][action] = Q[state][action] + learning_rate * (
    reward + discount_factor * max(Q[next_state]) - Q[state][action]
)
```

### Reward Function

Balances cost optimization with user satisfaction:

```python
def get_reward(self, price_index, start_time, energy_consumed):
    cost_component = (1-p) * price[price_index] * energy_consumed
    satisfaction_component = p * (k * (start_time - preferred_time))
    return 1 / (cost_component + satisfaction_component + epsilon)
```

## 📊 Data Sources

- **Electricity Prices**: [Nord Pool](https://www.nordpoolgroup.com/) (2013-2014)
- **EV Usage Patterns**: [Test-An-EV Project](http://smarthg.di.uniroma1.it/Test-an-EV)
- **Home Energy Data**: [SmartHG Project](http://smarthg.di.uniroma1.it)

## 🧪 Evaluation Metrics

The system evaluates performance using four key criteria:

1. **Δ% Energy Cost** - Total electricity cost reduction
2. **Δ% Energy Consumed** - Change in total energy consumption  
3. **Δ% Average Charging Price** - Average cost per kWh charged
4. **Δ% Average Final SOC** - Battery charge level achieved

**Overall Score**: `(1-ρ) × (cost_metrics) - ρ × (satisfaction_metrics)`

## 🛠️ Customization

### Adding New Battery Models

1. Create a new class inheriting from appropriate base class
2. Implement the `function()` method with your optimization logic
3. Add initialization in `insert_devices()` function
4. Configure parameters in the device list

### Modifying Reward Functions

Customize the reward calculation to reflect different optimization objectives:

```python
def custom_reward(self, price, energy, time_delay, battery_health):
    return weighted_sum([
        price_component(price, energy),
        comfort_component(time_delay), 
        longevity_component(battery_health)
    ])
```

## 📚 Research Context

This implementation is based on the research paper:

> Lu, Renzhi et al. "Demand Response for Home Energy Management Using Reinforcement Learning and Artificial Neural Network" IEEE Transactions on Smart Grid 10 (2019): 6629-6639.

**Key Contributions**:
- Extended original work to focus on EV integration
- Implemented four distinct battery management strategies
- Comparative analysis across multiple user preference scenarios
- Real-world data validation with Nordic electricity markets

## 🎓 Academic Usage

This project was developed as a bachelor's thesis in Computer Science at Sapienza University of Rome. If you use this work in academic research, please cite:

```bibtex
@mastersthesis{imperati2021hems,
  title={Valutazione di un Home Energy Management System basato su Reinforcement Learning},
  author={Imperati, Vincenzo},
  year={2021},
  school={Sapienza Università di Roma},
  type={Bachelor's thesis}
}
```

## 🔬 Future Enhancements

- [ ] **Real-time Integration** - Connect with actual smart home devices
- [ ] **Weather Integration** - Incorporate weather forecasting for better predictions
- [ ] **Solar Panel Support** - Add renewable energy generation optimization
- [ ] **Vehicle-to-Grid (V2G)** - Bidirectional energy flow capabilities
- [ ] **Mobile App Interface** - User-friendly control and monitoring
- [ ] **Cloud Deployment** - Scalable cloud-based implementation

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. **Algorithm Enhancements** - New optimization strategies
2. **Real-world Testing** - Hardware integration and validation
3. **User Interface** - Better visualization and control tools
4. **Documentation** - Code comments and usage examples
5. **Performance** - Optimization for larger scale deployments

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Vincenzo Imperati**
- 🎓 Computer Science Student, Sapienza University of Rome
- 📧 Email: imperati.1834930@studenti.uniroma1.it
- 👨‍🏫 Supervisor: Prof. Igor Melatti

## 🙏 Acknowledgments

- **Prof. Igor Melatti** - Thesis supervisor and guidance
- **Nord Pool** - Historical electricity price data
- **Test-An-EV Project** - Real-world EV usage patterns
- **SmartHG Project** - Home energy consumption datasets
- **IEEE Smart Grid Community** - Research foundation and inspiration