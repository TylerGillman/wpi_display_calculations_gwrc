# wpi_display_calculations_gwrc
This is the repo for the IQP 2026, GWRC project. This contains the files for the backend and front end of the custom display.

# GWRC WPI IQP 2026 – Planting Analysis Script

## Section Key

01. Description
02. Purpose
03. Requirements
04. Inputs
05. Key Fields
06. Processing Stages
07. Custom Popup
08. Notes
09. Authors
10. License

----------

## Description

This Python script is an **ArcGIS (ArcPy) geoprocessing tool** developed for the **WPI IQP 2026 Greater Wellington Regional Council (GWRC) project**.

The script calculates planting totals, survival metrics, monitoring coverage, density statistics, and park-level aggregations from monitoring point, site, and park feature classes.

It is designed to run as a toolbox script tool inside ArcGIS Pro and supports staged execution depending on user-selected checkboxes.

----------

## Purpose

The script automates calculation and updating of:

- Site-level planting totals (yearly and overall)
- Monitoring site counts and estimated monitored area
- Planting area (geodesic hectares)
- Survival and mortality rates
- Density metrics (plants per hectare)
- Estimated total plants per site and per park
- Park-level aggregated totals
- Park coverage percentage (planting area vs park area)

The workflow is structured into **three processing stages** that can be run independently or together.

----------

## Requirements

- ArcGIS Pro
- Python environment with `arcpy`
- Feature classes for:
  - Points layer (monitoring data)
  - Sites layer (planting areas)
  - Parks layer
- Required attribute fields must exist in the input layers

----------

## Inputs (Tool Parameters)

`points_layer` --  Monitoring points feature class
`sites_layer` -- Planting sites feature class
`parks_layer` -- Parks feature class
`run_full` -- Run all stages
`run_site` -- Run site-level calculations only
`run_park` -- Run park-level calculations

----------

## Key Fields Used

### ID Fields
- `SiteID`
- `ParkID`

### Area Fields
- `Point_Est_Area_ha`
- `Planting_Area_ha`
- `Park_Area_ha`

### Monitoring Fields
- `Numb_Monitor_Sites`
- `Monitoring_Sites_Per_Park`

### Derived Metrics
- `Site_Total_YYYY`
- `Park_Total_YYYY`
- `Total_Plants`
- `Survival_Rate_Raw`
- `Mortality_Rate_Raw`
- `Survival_Rate_Norm`
- `Mortality_Rate_Norm`
- `Initial_Density`
- `Current_Density`
- `Plants_Lost`
- `Coverage_Percentage`
- `Plant_Estimate`

----------

## Processing Stages

### Stage 1 – Site Metrics
Calculates and updates:

- Yearly plant totals per site
- Total plants per site
- Monitoring site counts
- Estimated monitored area
- Planting area (geodesic hectares)
- Site survival metrics
- Density calculations
- Estimated plant totals

### Stage 2 – Park Aggregation
Aggregates site values to park level:

- Yearly park totals
- Total plants per park
- Monitoring sites per park
- Park geodesic area
- Total planting area per park

### Stage 3 – Derived Park Analytics
Calculates:

- Raw and normalized survival rates
- Mortality rates
- Density per hectare
- Total plants lost
- Coverage percentage (planting area / park area)
- Park-level plant estimates

----------

## Custom Popup

These HTML files define the popups used in the map interface. 

Files included:
- `PopUp_General_Information_Parks.html`
- `PopUp_General_Information_Sites.html`
- `PopUp_Data_Visualization.html`
- `PopUp_General_Information_Points.html`
- `PopUp_Data_Visualization_Points.html`

----------

## Notes

- Zero values are converted to NULL where appropriate.
- Survival rates use oldest and most recent year fields.
- Monitoring area assumes a 9m radius.
- Geodesic area is calculated in hectares.

----------

## Authors

Developed for:
WPI Interactive Qualifying Project (IQP) 2026
Greater Wellington Regional Council (GWRC)

Authorship History:
Tyler Gillman: Wrote inital interation of program, including all functions, comments, and structure. Last edited 03/2026.

----------

## License

This project is licensed under the MIT License – see the LICENSE file for details.
