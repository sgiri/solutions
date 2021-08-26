
import sys
import yaml

import numpy as np
from model.new_unit_adoption import NewUnitAdoption as UnitAdoption
from model.solution import Solution

import json

class OceanSolution(Solution):
    """ This is the base class that each Ocean solution should inherit from.
    Contains all the calculations required for Ocean-based scenario results.
    """

    def _load_config_file(self, file_name):
        
        stream = open(file_name, 'r')
        config = yaml.load(stream, Loader=yaml.FullLoader)
        self.start_year = config['StartYear']
        self.end_year = config['EndYear']
        self.base_year = config['BaseYear']

        self.pds_adoption_file = config['PDSAdoptionFile']
        self.ref_adoption_file = config['REFAdoptionFile']
        self.scenarios_file = config['ScenariosFile']
        self.required_version_minimum = tuple(int(st) for st in str.split(config['RequiredVersionMinimum'], '.'))
        self._config = config

    def _load_adoption_scenario(self, adoption_input_file, adoption_scenario_name):
            
        try:
            ad_scenario = UnitAdoption(self.base_year, self.end_year, adoption_scenario_name, adoption_input_file)
        except ValueError as ev:
            print(ev.args)
            raise ValueError(f"Unable to initialise {adoption_scenario_name}")
        
        return ad_scenario

    def _load_pds_scenario(self):
        
        self.pds_scenario = self._load_adoption_scenario(self.pds_adoption_file,
                        self.scenario.pds_scenario_name)

        self.pds_scenario.first_cost = self.scenario.soln_first_cost
        self.pds_scenario.expected_lifetime = self.scenario.soln_expected_lifetime
        self.pds_scenario.net_profit_margin = self.scenario.soln_net_profit_margin
        self.pds_scenario.operating_cost = self.scenario.soln_operating_cost
        self.pds_scenario.sequestration_rate_all_ocean = self.scenario.sequestration_rate_all_ocean
        self.pds_scenario.disturbance_rate = self.scenario.disturbance_rate
        self.pds_scenario.growth_rate_of_ocean_degradation = self.scenario.growth_rate_of_ocean_degradation

        
    def _load_ref_scenario(self):
        
        self.ref_scenario = self._load_adoption_scenario(self.ref_adoption_file,
                        self.scenario.ref_scenario_name)
        
        self.ref_scenario.first_cost = self.scenario.soln_first_cost
        self.ref_scenario.expected_lifetime = self.scenario.soln_expected_lifetime
        self.ref_scenario.net_profit_margin = self.scenario.soln_net_profit_margin
        self.ref_scenario.operating_cost = self.scenario.soln_operating_cost
        self.ref_scenario.sequestration_rate_all_ocean = self.scenario.sequestration_rate_all_ocean
        self.ref_scenario.disturbance_rate = self.scenario.disturbance_rate
        self.ref_scenario.growth_rate_of_ocean_degradation = self.scenario.growth_rate_of_ocean_degradation


    # Initialize from configuration file:
    def __init__(self, configuration_file_name):
        self._load_config_file(configuration_file_name)
        if sys.version_info < self.required_version_minimum:
            print(f'Warning - you are running python version {sys.version}. Version {self.required_version_minimum} or greater is required.')


    def get_scenario_names(self):

        input_stream = open(self.scenarios_file, 'r')
        scen_dict = json.load(input_stream)
        
        return list(scen_dict.keys())
    

    def print_scenario_info(self):
        print('Loaded scenario name:', self.scenario.description)
        
    # Unit Adoption functions:

    def get_adoption_unit_increase_pds_vs_ref_final_year(self) -> np.float64:
        pds_series = self.pds_scenario.get_units_adopted() 
        ref_series = self.ref_scenario.get_units_adopted()

        net_series = pds_series.subtract(ref_series)

        return net_series.loc[self.end_year]
        
    def get_adoption_unit_increase_pds_final_year(self) -> np.float64:
        pds_series = self.pds_scenario.get_units_adopted() 
        return pds_series.loc[self.end_year]


    def get_global_percent_adoption_base_year(self) -> np.float64:
        # Adoption for base year, as a percentage of TOA.
        pds_series = self.pds_scenario.get_units_adopted()
        
        tam_series = self.pds_scenario.get_tam_units()
        pds_base_year = pds_series.loc[self.base_year+1]
        tam_base_year = tam_series.loc[self.base_year+1]
        result  = pds_base_year / tam_base_year
        return result


    def get_percent_adoption_start_year(self) -> np.float64:

        pds_series = self.pds_scenario.get_units_adopted()
        tam_series = self.pds_scenario.get_tam_units()

        pds_start_year = pds_series.loc[self.start_year]
        tam_start_year = tam_series.loc[self.start_year]

        result = pds_start_year / tam_start_year
        return result
    

    def get_percent_adoption_end_year(self) -> np.float64:
        pds_series = self.pds_scenario.get_units_adopted()
        tam_series = self.pds_scenario.get_tam_units()
        
        pds_start_year = pds_series.loc[self.end_year]
        tam_start_year = tam_series.loc[self.end_year]

        result = pds_start_year / tam_start_year
        return result



    ### Financial functions:

    def get_marginal_first_cost(self) -> np.float64:
        
        # pds_awfc corresponds to the "Annual World First Cost" column (solution-pds)
        # in [First Cost]!$E$36 in the spreadsheet.

        pds_awfc = self.pds_scenario.get_annual_world_first_cost()
        
        # ref_awfc corresponds to the "Annual World First Cost" column (solution-ref)
        # in [First Cost]!$N$36 in the spreadsheet.

        ref_awfc = self.ref_scenario.get_annual_world_first_cost()
        years = list(range(self.base_year, self.end_year +1))
        result = (pds_awfc - ref_awfc).loc[years]
        
        return result.sum() / 1000  # in billions

    
    def get_cumulative_first_cost_pds(self) -> np.float64:

        years = list(range(self.base_year, self.end_year +1))

        pds_fc = self.pds_scenario.get_annual_world_first_cost()

        result = pds_fc.loc[years]

        return result.sum() / 1000  # in billions


    
    def get_operating_cost(self) -> np.float64:

        # TODO: confirm start_year-1 is desired. Why does it start in 2019?

        # Each cell in pds_series should match SUM($C266:$AV266) in [Operating Cost] worksheet.

        pds_series = self.pds_scenario.get_operating_cost( self.end_year) * (1+ self.disturbance_rate)
        pds_result = pds_series.cumsum().loc[self.end_year] - pds_series.cumsum().loc[self.start_year]

        # Each cell in ref_series should match SUM($C403:$AV403) in [Operating Cost] worksheet.
        ref_series = self.ref_scenario.get_operating_cost( self.end_year) * (1+self.disturbance_rate)
        ref_result = ref_series.cumsum().loc[self.end_year] - ref_series.cumsum().loc[self.start_year]

        result = (ref_result - pds_result) / 1000 # in billions

        # result should match "Difference in Operating Cost (Reference - PDS)". [Operating Cost]!$C$125

        return result

    
    def get_lifetime_operating_savings(self) -> np.float64:
        
        # pds_series should match [Operating Cost]!$C$125 = "Difference in Operating Cost (Reference minus PDS)"
        pds_series = self.pds_scenario.get_lifetime_operating_savings(self.end_year) * (1+ self.disturbance_rate)

        # TODO: subtract this from conventional.

        result = - pds_series.sum()

        return result / 1_000 # express in billions of USD



    def get_lifetime_cashflow_npv_single(self, purchase_year) -> np.float64:

        discount_rate = self.npv_discount_rate
        pds_series = -1 * self.pds_scenario.get_lifetime_cashflow_npv(purchase_year, discount_rate)

        result = pds_series.sum()

        return result / 1_000 # express in billions of USD


    def get_payback_period_soln_only(self, purchase_year) -> np.float64:

        discount_rate = self.npv_discount_rate
        pds_series = -1 * self.pds_scenario.get_lifetime_cashflow_npv(purchase_year, discount_rate)

        cumulative_sum = pds_series.cumsum()

        max_val_index = cumulative_sum.argmax()
        max_val = cumulative_sum.iloc[max_val_index]

        return max_val


    def get_payback_period_soln_only_npv(self, purchase_year) -> np.float64:

        discount_rate = self.npv_discount_rate

        pds_series = -1 * self.pds_scenario.get_lifetime_cashflow_npv(purchase_year, discount_rate)

        cumulative_sum = pds_series.cumsum()

        max_val_index = cumulative_sum.argmax()
        max_val = cumulative_sum.iloc[max_val_index]

        return max_val


    def get_payback_period_soln_to_conv(self, purchase_year) -> np.float64:

        #$K$122 on Operating Cost spreadsheet tab.

        # Use discount rate of 0.0 to avoid discounting.
        discount_rate = 0.0

        # Don't use ref_series here, use "conventional" series instead.
        # Since the "conventional" concept isn't applicable for seaweed farming, just use a zero timeseries.

        pds_series = self.pds_scenario.get_lifetime_cashflow_npv(purchase_year, discount_rate)

        net_series = -pds_series

        cumulative_sum = net_series.cumsum()

        max_val_index = cumulative_sum.argmax()
        max_val = cumulative_sum.iloc[max_val_index]

        return max_val


    def get_payback_period_soln_to_conv_npv(self, purchase_year) -> np.float64:

        discount_rate = self.npv_discount_rate

        # Don't use ref_series here, use "conventional" series instead.
        # Since the "conventional" concept isn't applicable for seaweed farming, just use a zero timeseries.

        pds_series = self.pds_scenario.get_lifetime_cashflow_npv(purchase_year, discount_rate)
        net_series =  -pds_series

        cumulative_sum = net_series.cumsum()

        max_val_index = cumulative_sum.argmax()
        max_val = cumulative_sum.iloc[max_val_index]

        return max_val


    def get_lifetime_cashflow_npv_all(self) -> np.float64:
        
        # calculation matches "NPV" timeseries from [Operating Cost]!$E$125

        # TODO fc should be fc diff, so do the same thing for ref scenario and find diff.
        ref_fc = self.ref_scenario.get_annual_world_first_cost()
        pds_fc = self.pds_scenario.get_annual_world_first_cost()

        net_fc = ref_fc - pds_fc

        # fc_clipped should match "Investment (Reference First Cost minus PDS First Cost)" timeseries from [Operating Cost]!$B$125
        fc_clipped = net_fc.loc[self.start_year-1:self.end_year]

        # TODO op_cost should be op_cost diff, so do the same thing for ref scenario and find diff.
        # op_cost matches "Difference in Operating Cost (ref - pds)"" timeseries from [Operating Cost]!$C$125

        op_cost = - self.pds_scenario.get_lifetime_operating_savings(self.end_year) * (1+ self.disturbance_rate)

        net_cash_flow = fc_clipped.add(op_cost, fill_value = 0.0)

        rate = self.npv_discount_rate
        discount_factor = 1/(1+rate)

        num_rows = net_cash_flow.shape[0]

        discount_factors = [discount_factor**(row+1) for row in range(num_rows)]

        npv = net_cash_flow.multiply(discount_factors, axis = 'index')
        
        result = npv.sum()
        
        return result / 1_000 # express in billions of USD


    def get_abatement_cost(self) -> np.float64:

        total_co2_reduction = self.get_total_co2_seq()

        pds_fc = self.pds_scenario.get_annual_world_first_cost()
        ref_fc = self.ref_scenario.get_annual_world_first_cost()

        # following should be [(ref_fc + conv_fc) - pds_fc], however haven't implemented conventional yet (not relevant for seaweed farming).
        net_fc = ref_fc - pds_fc

        # after executing this next line, fc_clipped should match time series in [Operating Cost]!$B$125
        fc_clipped = net_fc.loc[self.start_year-1:self.end_year]

        pds_op_cost = self.pds_scenario.get_lifetime_operating_savings(self.end_year)
        ref_op_cost = self.ref_scenario.get_lifetime_operating_savings(self.end_year)

        # after executing this next line, net_op_cost should match time series in [Operating Cost]!$C$125
        net_op_cost = (ref_op_cost -pds_op_cost) * (1+ self.disturbance_rate)

        net_cash_flow = fc_clipped.add(net_op_cost).fillna(0.0)
        
        rate = self.npv_discount_rate
        discount_factor = 1/(1+rate)

        num_rows = net_cash_flow.shape[0]

        discount_factors = [discount_factor**(row+1) for row in range(num_rows)]

        npv = net_cash_flow.multiply(discount_factors, axis='index')
        npv_summed = npv.loc[self.start_year: self.end_year].sum()

        result = -1 * npv_summed/total_co2_reduction

        return result / 1_000 # express in billions of USD


    def get_net_profit_margin(self) -> np.float64:

        margin_series = self.pds_scenario.get_net_profit_margin(self.end_year) * (1- self.disturbance_rate)
        margin_series_cum = margin_series.cumsum()

        end_year_val = margin_series_cum.loc[self.end_year]
        start_year_val = margin_series_cum.loc[self.start_year]

        result = end_year_val - start_year_val
        
        return result / 1_000 # express in billions of USD


    def get_lifetime_profit_margin(self) -> np.float64:

        margin_series = self.pds_scenario.get_net_profit_margin(self.end_year) * (1- self.disturbance_rate)

        result  = margin_series.sum()

        return result / 1_000 # express in billions of USD

    def get_total_emissions_reduction(self):
        series = self.pds_scenario.total_at_risk_area

        return


    def get_total_co2_seq(self) -> np.float64:
        
        pds_sequestration = self.pds_scenario.get_carbon_sequestration(self.sequestration_rate_all_ocean, self.disturbance_rate)
        ref_sequestration = self.ref_scenario.get_carbon_sequestration(self.sequestration_rate_all_ocean, self.disturbance_rate)
        # net_sequestration should equal 'CO2-eq PPM Calculator' on tab [CO2 Calcs]!$B$224
        net_sequestration = (pds_sequestration - ref_sequestration)

        result = net_sequestration.loc[self.start_year+1 : self.end_year].sum()

        return result / 1_000 # express in billions of USD


    def get_change_in_ppm_equiv(self, delay_period = 0) -> np.float64:
        
        pds_sequestration = self.pds_scenario.get_change_in_ppm_equiv_series()
        ref_sequestration = self.ref_scenario.get_change_in_ppm_equiv_series()

        net_sequestration = (pds_sequestration - ref_sequestration)
        # net_sequestration should now equal 'CO2-eq PPM Calculator' on tab [CO2 Calcs]!$B$224

        end = self.end_year
        if delay_period > 0:
            end -= delay_period
        result = net_sequestration.loc[end]

        return result


    def get_change_in_ppm_equiv_final_year(self) -> np.float64:
                
        pds_sequestration = self.pds_scenario.get_change_in_ppm_equiv_series()
        ref_sequestration = self.ref_scenario.get_change_in_ppm_equiv_series()
        # net_sequestration should equal 'CO2-eq PPM Calculator' on tab [CO2 Calcs]!$B$224
        net_sequestration = (pds_sequestration - ref_sequestration)
        
        result = net_sequestration.loc[self.end_year] - net_sequestration.loc[self.end_year-1]

        return result
        

    def get_max_annual_co2_sequestered(self) -> np.float64:

        pds_sequestration = self.pds_scenario.get_carbon_sequestration(
            self.sequestration_rate_all_ocean,
            self.disturbance_rate,
            self.growth_rate_of_ocean_degradation,
            self.delay_impact_of_protection_by_one_year)

        ref_sequestration = self.ref_scenario.get_carbon_sequestration(
            self.sequestration_rate_all_ocean,
            self.disturbance_rate,
            self.growth_rate_of_ocean_degradation,
            self.delay_impact_of_protection_by_one_year)

        # sequestration should match the time series in [CO2 Calcs]!$B$120
        net_sequestration = (pds_sequestration - ref_sequestration)

        start = self.start_year
        end = self.end_year
        if self.delay_regrowth_of_degraded_land_by_one_year:
            end -= 1
            start -= 1
        
        result = max(net_sequestration.loc[start:end])

        return result / 1_000


    def get_co2_sequestered_final_year(self) -> np.float64:

        pds_sequestration = self.pds_scenario.get_carbon_sequestration(
            self.sequestration_rate_all_ocean,
            self.disturbance_rate,
            self.growth_rate_of_ocean_degradation,
            self.delay_impact_of_protection_by_one_year)

        ref_sequestration = self.ref_scenario.get_carbon_sequestration(
            self.sequestration_rate_all_ocean,
            self.disturbance_rate,
            self.growth_rate_of_ocean_degradation,
            self.delay_impact_of_protection_by_one_year)
        
        net_sequestration = (pds_sequestration - ref_sequestration)

        end = self.end_year
        if self.delay_regrowth_of_degraded_land_by_one_year:
            end -= 1
        
        result = net_sequestration.loc[end]

        return result / 1_000

