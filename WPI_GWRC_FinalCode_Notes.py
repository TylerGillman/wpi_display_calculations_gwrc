"""
WPI IQP 2026 - GWRC Park Planting Analysis Script

This script processes planting and monitoring data across three GIS layers:
    1. Points layer (monitoring points)
    2. Sites layer (planting sites)
    3. Parks layer (regional parks)

The workflow calculates:
    - Site-level yearly and total plant counts
    - Monitoring site counts and estimated monitored area
    - Geodesic planting area per site
    - Site-level survival and density metrics
    - Park-level aggregated totals
    - Area-weighted survival rates
    - Coverage percentages
    - Plant population estimates

The script runs in three stages:
    Stage 1 - Site Metrics
    Stage 2 - Park Aggregation
    Stage 3 - Derived Park Analytics

Outputs are written directly back to the Sites and Parks feature layers.

Author: Tyler Gillman
Project: WPI IQP 2026 - Greater Wellington Regional Council
Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""
import arcpy
import datetime
import math
# =========================================
# Script for WPI IQP 2026 GWRC project 
# =========================================
# User inputs from the tool
points_layer = arcpy.GetParameterAsText(0)      # Points layer
sites_layer = arcpy.GetParameterAsText(1)       # Sites layer
parks_layer = arcpy.GetParameterAsText(2)       # Parks layer 
run_full = arcpy.GetParameter(3)       # Planting totals checkbox
run_site = arcpy.GetParameter(4)           # Site area checkbox
run_park = arcpy.GetParameter(5)           # Park area checkbox
# Global variables and field names
site_id_field = "SiteID"                        # Unique site ID field
park_id_field = "ParkID"                        # Unique park ID field
monitoring_site_field = "Point_Est_Area_ha"     # Monioring site estimate for normalization
planting_area_field = "Planting_Area_ha"        # Planting area for normalization
park_area_field = "Park_Area_ha"                # Park area for normalization
monitoring_field = "Monitoring_Sites_Per_Park"  # Monitoring sites per park
points_fields = [f.name for f in arcpy.ListFields(points_layer)]
sites_fields = [f.name for f in arcpy.ListFields(sites_layer)]
parks_fields = [f.name for f in arcpy.ListFields(parks_layer)]
# =========================================
# Toolbox functions 
# =========================================
# safely convert to integer or none
def safe_int_or_null(value):
    """
    Safely converts a value to an integer.

    Converts numeric or string representations of numbers into integers.
    Returns None if the value is None or cannot be converted.

    Args:
        value: Any numeric or string value.
    Returns:
        int or None: Converted integer value, or None if invalid.
    """
    if value is None:
        return None
    try:
        return int(float(value))
    except:
        return None
# log time stamped messages
def log(msg):
    """
    Logs a timestamped message to the ArcGIS tool output.

    Args:
        msg (str): Message to display.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    arcpy.AddMessage(f"[{timestamp}] {msg}")
# =========================================
# PRIMARY CALCULATION FUNCTIONS 
# =========================================
# Calculate site totals for each year and overall, then update sites layer
def calculateSiteTotals():
    """
    Calculates yearly and total plant counts per site.

    Aggregates Plants_YYYY fields from the points layer,
    sums values per SiteID, and writes yearly totals and
    overall totals back to the sites layer.

    Zero totals are converted to None for cleaner reporting.

    Outputs:
        Updates Site_Total_YYYY fields and Total_Plants
        in the sites layer.
    """
    log(f"RUNNING: calculateSiteTotals()")
    # Get Plants_YYYY fields from points layer
    plants_fields = [f for f in points_fields if f.startswith("Plants_")]
    plants_fields = sorted(plants_fields, key=lambda x: int(x.split("_")[-1]))
    totals_fields = ["Site_Total_" + f.split("_")[-1] for f in plants_fields]
    # Build dictionary of totals per site
    site_totals = {}
    with arcpy.da.SearchCursor(points_layer, [site_id_field] + plants_fields) as cursor:
        for row in cursor:
            site_id = str(row[0])
            if site_id is None:
                continue  # Skip rows with null SiteID
            if site_id not in site_totals:
                site_totals[site_id] = [0] * len(plants_fields) # Initialize totals list with 0s
            for i in range(len(plants_fields)):
                value = row[i + 1]
                if value is None:
                    continue
                try:
                    site_totals[site_id][i] += int(value)
                except:
                    continue
    # Update sites layer with totals
    update_fields = [site_id_field] + totals_fields + ["Total_Plants"]
    with arcpy.da.UpdateCursor(sites_layer, update_fields) as cursor:
        for row in cursor:
            site_id = row[0]
            if site_id in site_totals:
                yearly_totals = site_totals[site_id]
                # Store yearly totals (0 becomes None)
                for idx, val in enumerate(yearly_totals):
                    row[1 + idx] = val if val != 0 else None
                real_values = [v for v in yearly_totals if v != 0]
                row[-1] = sum(real_values) if real_values else None
            else:
                for i in range(1, len(update_fields)):
                    row[i] = None
            cursor.updateRow(row)
    log(f"COMPLETE: Site yearly and overall totals updated successfully.")
# Calculate number of monitoring sites and eastimated area per site
def calculateMonitoringSiteCountsAndArea():
    """
    Calculates monitoring point counts and estimated monitored area per site.

    Counts the number of monitoring points per SiteID and
    estimates monitored area using a fixed-radius circular plot.

    Outputs:
        Updates Numb_Monitor_Sites and Point_Est_Area_ha
        in the sites layer.
    """
    log(f"RUNNING: calculateMonitoringSiteCountsAndArea()")
    # Fields
    count_field = "Numb_Monitor_Sites"
    radius_m = 9
    point_area_ha = math.pi * radius_m**2 / 10000  # convert to ha
    # Count points per site
    site_counts = {}
    with arcpy.da.SearchCursor(points_layer, [site_id_field]) as cursor:
        for row in cursor:
            site_id = row[0]
            if site_id is None:
                continue
            site_counts[site_id] = site_counts.get(site_id, 0) + 1
    # Write counts and estimated area to sites_layer
    update_fields = [site_id_field, count_field, monitoring_site_field]
    with arcpy.da.UpdateCursor(sites_layer, update_fields) as cursor:
        for row in cursor:
            site_id = row[0]
            count = site_counts.get(site_id, 0)
            if count > 0:
                row[1] = count
            else:
                row[1] = None
            estimated_area = count * point_area_ha
            if estimated_area == 0:
                row[2] = None
            else:
                row[2] = estimated_area
            cursor.updateRow(row)
    log(f"COMPLETE: Monitoring site counts and estimated areas updated successfully.")
# Calculate planting area size using geodesic area
def calculatePlantingAreaSize():
    """
    Calculates geodesic planting area per site.

    Uses ArcGIS CalculateGeometryAttributes to compute
    AREA_GEODESIC in hectares.

    Outputs:
        Updates Planting_Area_ha field in sites layer.
    """
    log(f"RUNNING: calculatePlantingAreaSize()")
    workspace = arcpy.Describe(sites_layer).path
    editor = arcpy.da.Editor(workspace)    
    editor.stopOperation()
    arcpy.management.CalculateGeometryAttributes(
        sites_layer,
        [[planting_area_field, "AREA_GEODESIC"]],
        area_unit="HECTARES"
    )
    editor.startOperation()
    log(f"COMPLETE: Planting area calculated successfully.")
# Calculate survival percentage per site
def calculateSiteSurvival():
    """
    Calculates site-level survival, mortality, density, and plant estimates.

    Uses oldest and most recent Site_Total_YYYY fields to compute:
        - Survival_Rate_Raw
        - Mortality_Rate_Raw
        - Initial and Current plant densities
        - Plants_Lost
        - Plant_Estimate (scaled to total planting area)

    Outputs:
        Updates multiple derived metric fields in the sites layer.
    """
    log(f"RUNNING: calculateSiteSurvival()")
    site_year_fields = sorted(
        [f for f in sites_fields if f.startswith("Site_Total_")],
        key=lambda x: int(x.split("_")[-1])
    )
    oldest_site_year_field = site_year_fields[0]
    current_site_year_field = site_year_fields[-1]
    # Prepare update cursor
    site_cursor_fields = [
        site_id_field,
        oldest_site_year_field,
        current_site_year_field,
        monitoring_site_field,
        "Initial_Plants_Alive",
        "Current_Plants_Alive",
        "Survival_Rate_Raw",
        "Mortality_Rate_Raw",
        "Initial_Density",
        "Current_Density",
        "Plants_Lost",
        "Plant_Estimate",
        "Planting_Area_ha"
    ]
    # Build field index dictionary
    site_field_index = {name: i for i, name in enumerate(site_cursor_fields)}
    # Modify Site Layer
    with arcpy.da.UpdateCursor(sites_layer, site_cursor_fields) as cursor:
        for row in cursor:
            initial = safe_int_or_null(row[site_field_index[oldest_site_year_field]])
            current = safe_int_or_null(row[site_field_index[current_site_year_field]])
            area_ha = (row[site_field_index[monitoring_site_field]])
            ## Store raw plant counts into reporting fields
            row[site_field_index["Initial_Plants_Alive"]] = initial
            row[site_field_index["Current_Plants_Alive"]] = current
            ## Raw Survival Percentage
            if initial in (None, 0) or current is None:
                survival_raw = None
                mortality_raw = None
            else:
                survival_raw = round((current / initial) * 100, 1)
                mortality_raw = round(100 - survival_raw, 1)
            row[site_field_index["Survival_Rate_Raw"]] = survival_raw
            row[site_field_index["Mortality_Rate_Raw"]] = mortality_raw  # For pie chart only
            ## Initial Density (plants per hectare)
            if area_ha in (None, 0):
                density_initial = None
            else:
                if initial is None:
                    density_initial = None
                else:
                    density_initial = initial / area_ha
            row[site_field_index["Initial_Density"]] = density_initial
            ## Current Density (plants per hectare)
            if area_ha in (None, 0):
                density_current = None
            else:
                if current is None:
                    density_current = None
                else:
                    density_current = current / area_ha
            row[site_field_index["Current_Density"]] = density_current
            ## Plants Lost
            if initial is None or current is None:
                loss = None
            else:
                loss = initial - current
            row[site_field_index["Plants_Lost"]] = loss
            ## Plant Estimate (current density * planting area)
            plant_estimate = None
            site_size_ha = row[site_field_index["Planting_Area_ha"]] or None
            if density_current is not None and site_size_ha is not None:
                plant_estimate = density_current * site_size_ha
            row[site_field_index["Plant_Estimate"]] = plant_estimate
            cursor.updateRow(row)
    log(f"COMPLETED: Site survival metrics calculated successfully.")
# Calculate number of monitoring sites per park by summing site totals
def calculateMonitoringSiteCountPerPark():
    """
    Aggregates monitoring site counts from sites to parks.

    Sums Numb_Monitor_Sites per ParkID and writes
    Monitoring_Sites_Per_Park to parks layer.
    """
    log(f"RUNNING: calculateMonitoringSiteCountPerPark()")
    sites_count_field = "Numb_Monitor_Sites"
    parks_count_field = "Monitoring_Sites_Per_Park"
    # Build park totals
    park_totals = {}
    with arcpy.da.SearchCursor(sites_layer, [park_id_field, sites_count_field]) as cursor:
        for row in cursor:
            park_id = row[0]
            site_count = row[1] or 0
            if park_id is None:
                continue
            park_totals[park_id] = park_totals.get(park_id, 0) + site_count
    # Update parks layer
    with arcpy.da.UpdateCursor(parks_layer, [park_id_field, parks_count_field]) as cursor:
        for row in cursor:
            park_id = row[0]
            row[1] = park_totals.get(park_id, 0)
            if row[1] == 0:
                row[1] = None
            cursor.updateRow(row)
    log(f"COMPLETED: Monitoring site counts per park updated successfully.")
# Calculate park totals by summing site totals
def calculateParkTotals():
    """
    Aggregates yearly and total plant counts from sites to parks.

    Sums Site_Total_YYYY values by ParkID and writes:
        - Park_Total_YYYY
        - Total_Plants

    Also updates monitoring site totals per park.
    """
    log(f"STARTED: Calculating plant totals per park...")
    calculateMonitoringSiteCountPerPark() # Update monitoring site counts per park
    site_total_fields = sorted(
        [f for f in sites_fields if f.startswith("Site_Total_")],
        key=lambda x: int(x.split("_")[-1])
    )
    total_park_fields = ["Park_Total_" + f.split("_")[-1] for f in site_total_fields]
    grand_total_field = "Total_Plants"
    # Build dictionary of totals per park
    park_totals = {}
    with arcpy.da.SearchCursor(sites_layer, [park_id_field] + site_total_fields) as cursor:
        for row in cursor:
            park_id = row[0]
            if park_id not in park_totals:
                park_totals[park_id] = [0] * len(site_total_fields)
            for i, field_name in enumerate(site_total_fields):
                value = row[i + 1]
                if value is None:
                    continue
                try:
                    numeric_value = int(value)
                    park_totals[park_id][i] += numeric_value
                except:
                    continue
    # Update parks layer with totals
    update_fields = [park_id_field] + total_park_fields + [grand_total_field, monitoring_field]
    with arcpy.da.UpdateCursor(parks_layer, update_fields) as cursor:
        for row in cursor:
            park_id = row[0]
            if park_id in park_totals:
                yearly_totals = park_totals[park_id]
                yearly_totals = [v if v != 0 else None for v in yearly_totals] # Force None for zeros
                real_values = [v for v in yearly_totals if v is not None] # Calculate grand total safely
                grand_total = sum(real_values) if real_values else None
                row[1:1 + len(total_park_fields)] = yearly_totals # Assign yearly totals
                row[1 + len(total_park_fields)] = grand_total # Assign grand total
            else:
                row[1:1 + len(total_park_fields)] = [None] * len(total_park_fields)
                row[1 + len(total_park_fields)] = None  # grandtotal
                row[1 + len(total_park_fields) + 1] = None  # monitoring field
            cursor.updateRow(row)
    log(f"COMPLETED: Park totals calculated and updated successfully.")
# Calculate park area size using geodesic area
def calculateParkAreaSize():
    """
    Calculates geodesic park area in hectares.

    Uses CalculateGeometryAttributes to compute AREA_GEODESIC.

    Outputs:
        Updates Park_Area_ha field in parks layer.
    """
    log(f"RUNNING: calculateParkAreaSize()")
    workspace = arcpy.Describe(parks_layer).path
    editor = arcpy.da.Editor(workspace)
    editor.stopOperation()
    arcpy.management.CalculateGeometryAttributes(
        parks_layer,
        [[park_area_field, "AREA_GEODESIC"]],
        area_unit="HECTARES"
    )
    editor.startOperation()
    log(f"Park area calculated successfully.")
# Helper function to calculate coverage percentage
def calculateCoveragePercentage():
    """
    Calculates total planting area per park.

    Sums Planting_Area_ha from sites layer by ParkID.

    Returns:
        dict: Mapping of ParkID to total planting area (ha).
    """
    log(f"RUNNING: calculateCoveragePercentage()")
    park_planting_totals = {} # Dictionary to hold total planting area per park
    with arcpy.da.SearchCursor(sites_layer, ["ParkID", "Planting_Area_ha"]) as cursor:
        for park_id, planting_ha in cursor:
            if park_id is None:
                continue
            planting_ha = planting_ha or 0
            if park_id not in park_planting_totals:
                park_planting_totals[park_id] = 0
            park_planting_totals[park_id] += planting_ha
            if park_planting_totals[park_id] == 0:
                park_planting_totals[park_id] = None  # Set to None if total is 0
    log(f"COMPLETED: Total planting area per park calculated successfully.")
    return park_planting_totals
# Helper function to calculate plant predictions by park
def calculatePlantPredictionsByPark(sites_layer, park_id_field, prediction_field):
    """
    Aggregates predicted plant counts per park.

    Sums the specified prediction field from sites layer
    grouped by ParkID.

    Returns:
        dict: Mapping of ParkID to total predicted plants.
    """
    log(f"RUNNING: calculatePlantPredictionsByPark()")
    totals = {}
    with arcpy.da.SearchCursor(sites_layer, [park_id_field, prediction_field]) as cursor:
        for park_id, prediction in cursor:
            if prediction is None:
                continue
            if park_id not in totals:
                totals[park_id] = 0
            totals[park_id] += prediction
    log(f"COMPLETED: Plant predictions by park calculated successfully.")
    return totals
# Helper function to calculate area-weighted survival percentage per park
def calculateAreaWeightedSurvival():
    """
    Calculates area-weighted survival rate per park.

    Uses Survival_Rate_Raw and Planting_Area_ha from sites layer.
    Larger planting areas contribute proportionally more weight.

    Returns:
        dict: Mapping of ParkID to normalized survival percentage.
    """
    log("RUNNING: calculateAreaWeightedSurvival()")
    weighted_survival = {}
    weighted_area_totals = {}
    with arcpy.da.SearchCursor(
        sites_layer,
        [park_id_field, "Survival_Rate_Raw", "Planting_Area_ha"]
    ) as cursor:
        for park_id, survival_pct, area in cursor:
            # Safety checks
            if park_id is None:
                continue
            if survival_pct in (None, 0):
                continue
            if area in (None, 0):
                continue
            # Convert percentage back to ratio
            survival_ratio = survival_pct / 100.0
            if park_id not in weighted_survival:
                weighted_survival[park_id] = 0
                weighted_area_totals[park_id] = 0
            weighted_survival[park_id] += survival_ratio * area
            weighted_area_totals[park_id] += area
    # Calculate final weighted survival percentage per park
    normalized_survival = {}
    for park_id in weighted_survival:
        total_area = weighted_area_totals.get(park_id, 0)
        if total_area > 0:
            normalized_survival[park_id] = round(
                (weighted_survival[park_id] / total_area) * 100,
                1
            )
        else:
            normalized_survival[park_id] = None
    log("COMPLETED: Area-weighted survival calculated successfully.")
    return normalized_survival
# Calculate park survival per park
def calculateParkSurvival():
    """
    Calculates park-level survival, mortality, density, coverage,
    and plant prediction metrics.

    Computes:
        - Raw survival (based on aggregated totals)
        - Area-weighted normalized survival
        - Density metrics
        - Coverage percentage (planting area / park area)
        - Total predicted plants

    Outputs:
        Updates multiple derived metric fields in parks layer.
    """
    log(f"RUNNING: calculateParkSurvival()")
    park_year_fields = sorted(
        [f for f in parks_fields if f.startswith("Park_Total_")],
        key=lambda x: int(x.split("_")[-1])
    )
    oldest_park_year_field = park_year_fields[0]
    current_park_year_field = park_year_fields[-1]
    # Get park area for density calculations
    park_prediction_totals = calculatePlantPredictionsByPark(sites_layer, park_id_field, "Plant_Estimate")
    # Get the planting totals per park
    park_planting_totals = calculateCoveragePercentage() 
    # Get area-weighted survival percentages per park
    park_normalized_survival = calculateAreaWeightedSurvival()
    # Prepare update cursor
    park_cursor_fields = [
        park_id_field,
        oldest_park_year_field,
        current_park_year_field,
        park_area_field,
        "Initial_Plants_Alive",
        "Current_Plants_Alive",
        "Survival_Rate_Raw",
        "Mortality_Rate_Raw",
        "Survival_Rate_Norm",
        "Mortality_Rate_Norm",
        "Initial_Density",
        "Current_Density",
        "Plants_Lost",
        "Coverage_Percentage",
        "Plant_Estimate"
    ]
    # Build field index dictionary
    park_field_index = {name: i for i, name in enumerate(park_cursor_fields)}
    # Modify Park Layer
    with arcpy.da.UpdateCursor(parks_layer, park_cursor_fields) as cursor:
        for row in cursor:
            initial = safe_int_or_null(row[park_field_index[oldest_park_year_field]])
            current = safe_int_or_null(row[park_field_index[current_park_year_field]])
            area_ha = row[park_field_index[park_area_field]]
            ## Store raw plant counts into reporting fields
            row[park_field_index["Initial_Plants_Alive"]] = initial
            row[park_field_index["Current_Plants_Alive"]] = current
            ## Raw Survival Percentage
            if initial in (None, 0) or current is None:
                survival_raw = None
                mortality_raw = None
            else:
                survival_raw = round((current / initial) * 100, 1)
                mortality_raw = round(100 - survival_raw, 1)
            row[park_field_index["Survival_Rate_Raw"]] = survival_raw
            row[park_field_index["Mortality_Rate_Raw"]] = mortality_raw  # For pie chart only
            ## Normalized Survival Percentage
            park_id = row[park_field_index[park_id_field]]
            survival_norm = park_normalized_survival.get(park_id)
            if survival_norm is not None:
                mortality_norm = round(100 - survival_norm, 1)
            else:
                mortality_norm = None
            if survival_norm == 0:
                survival_norm = None  # Set to None if survival is zero for clarity
                mortality_norm = None  # Set to None if mortality is zero for clarity
            row[park_field_index["Survival_Rate_Norm"]] = survival_norm
            row[park_field_index["Mortality_Rate_Norm"]] = mortality_norm  # For pie chart only
            ## Initial Density (plants per hectare)
            if area_ha in (None, 0):
                density_initial = None
            else:
                if initial is None:
                    density_initial = None
                else:
                    density_initial = initial / area_ha
            row[park_field_index["Initial_Density"]] = density_initial
            ## Current Density (plants per hectare)
            if area_ha in (None, 0):
                density_current = None
            else:
                if current is None:
                    density_current = None
                else:
                    density_current = current / area_ha
            row[park_field_index["Current_Density"]] = density_current
            ## Plants Lost
            if initial is None or current is None:
                loss = None
            else:
                loss = initial - current
            row[park_field_index["Plants_Lost"]] = loss
            ## Coverage Percentage (PLANTING AREA / PARK AREA)
            park_id = row[park_field_index[park_id_field]]
            park_ha = area_ha or 0
            if park_id in park_planting_totals:
                total_planting = park_planting_totals[park_id]
            else:
                total_planting = 0
            if park_ha > 0:
                coverage_pct = round((total_planting / park_ha) * 100, 2)
                if coverage_pct == 0:
                    coverage_pct = None  # Set to None if coverage is zero for clarity
            else:
                coverage_pct = None
            row[park_field_index["Coverage_Percentage"]] = coverage_pct
            ## Total Plant Estimate (sum of site estimates)
            park_id = row[park_field_index[park_id_field]]
            if park_id in park_prediction_totals:
                total_prediction = park_prediction_totals[park_id]
            else:
                total_prediction = None
            row[park_field_index["Plant_Estimate"]] = total_prediction 
            cursor.updateRow(row)
    log(f"COMPLETED: Park survival metrics calculated successfully.")
#
#
#
# =========================================
# Main pipeline functions
# =========================================
def run_stage1():
    """
    Executes Stage 1 - Site Metrics.

    Runs:
        - Site totals
        - Monitoring site counts
        - Planting area calculation
        - Site survival metrics

    All edits occur within a single edit session.
    """
    log("===== STAGE 1: SITE METRICS =====")
    workspace = arcpy.Describe(sites_layer).path
    editor = arcpy.da.Editor(workspace)
    editor.startEditing(False, True)
    editor.startOperation()
    calculateSiteTotals()
    calculateMonitoringSiteCountsAndArea()
    calculatePlantingAreaSize()
    calculateSiteSurvival()
    editor.stopOperation()
    editor.stopEditing(True)
    log("Stage 1 complete.")
def run_stage2():
    """
    Executes Stage 2 - Park Aggregation.

    Runs:
        - Park totals
        - Monitoring site counts per park
        - Park area calculation
        - Coverage percentage calculation
    """
    log("===== STAGE 2: PARK AGGREGATION =====")
    workspace = arcpy.Describe(parks_layer).path
    editor = arcpy.da.Editor(workspace)
    editor.startEditing(False, True)
    editor.startOperation()
    calculateParkTotals()
    calculateMonitoringSiteCountPerPark()
    calculateParkAreaSize()
    calculateCoveragePercentage()
    editor.stopOperation()
    editor.stopEditing(True)
    log("Stage 2 complete.")
def run_stage3():
    """
    Executes Stage 3 - Derived Park Analytics.

    Runs:
        - Park survival calculations
        - Normalized survival metrics
        - Density and coverage outputs
    """
    log("===== STAGE 3: DERIVED PARK ANALYTICS =====")
    workspace = arcpy.Describe(parks_layer).path
    editor = arcpy.da.Editor(workspace)
    editor.startEditing(False, True)
    editor.startOperation()
    calculateParkSurvival()
    editor.stopOperation()
    editor.stopEditing(True)
    log("Stage 3 complete.")
def run_pipeline(run_site, run_park, run_full):
    """
    Controls execution of the full processing pipeline.

    Execution logic:
        - run_full: runs all stages
        - run_park: runs Stage 1, 2, and 3
        - run_site: runs Stage 1 only

    Args:
        run_site (bool): Site-level processing flag.
        run_park (bool): Park-level processing flag.
        run_full (bool): Full pipeline flag.
    """
    stage1 = False
    stage2 = False
    stage3 = False
    if run_full:
        stage1 = stage2 = stage3 = True
    elif run_park:
        stage1 = True
        stage2 = True
        stage3 = True
    elif run_site:
        stage1 = True
    if stage1:
        run_stage1()
    if stage2:
        run_stage2()
    if stage3:
        run_stage3()
run_pipeline(run_site, run_park, run_full) # Execute the pipeline based on user selections