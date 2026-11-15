;FLAVOR:Marlin
;TIME:1
;Filament used: 0m
;Layer height: 0.2
;MINX:0
;MINY:0
;MINZ:0.2
;MAXX:0
;MAXY:0
;MAXZ:0.2
;TARGET_MACHINE.NAME:Unknown
;Generated with Cura_SteamEngine 5.13.0
M104 S210
M105
M109 S210
G21 ; Use millimeters
G90 ; Absolute XYZ positioning
M82 ; Absolute extrusion
G28 ;Home
G1 Z15.0 F300 ;Move the nozzle up 15mm
;Prime the extruder
G92 E0
G1 F200 E3
G92 E0
M82 ;absolute extrusion mode
G92 E0
G92 E0
G1 F1500 E-6.5
;LAYER_COUNT:1
;LAYER:0
M106 S255
G0 F3600 Z0.2
;TIME_ELAPSED:1.931892
M107
M104 S0
M140 S0

; Lift before moving toward home
G91 ; Relative positioning
G1 Z5 F300 ; Raise nozzle clearance by 5 mm

G90 ; Restore absolute XYZ positioning
M82 ; Restore absolute extrusion
G1 X0 Y0 F900 ; Move to X = 0, Y = 0 at 15 mm/s

M400 ; Wait for movement to finish
M84 ; Disable motors
M82 ;absolute extrusion mode
M104 S0
;End of Gcode
;SETTING_3 {"global_quality": "[general]\\nversion = 4\\nname = Ambot 0.2mm\\nde
;SETTING_3 finition = custom\\n\\n[metadata]\\ntype = quality_changes\\nquality_
;SETTING_3 type = draft\\nsetting_version = 27\\n\\n[values]\\nadhesion_type = n
;SETTING_3 one\\nlayer_height_0 = 0.2\\n\\n", "extruder_quality": ["[general]\\n
;SETTING_3 version = 4\\nname = Ambot 0.2mm\\ndefinition = custom\\n\\n[metadata
;SETTING_3 ]\\ntype = quality_changes\\nquality_type = draft\\nintent_category =
;SETTING_3  default\\nposition = 0\\nsetting_version = 27\\n\\n[values]\\nconnec
;SETTING_3 t_skin_polygons = False\\ninset_direction = outside_in\\nmaterial_pri
;SETTING_3 nt_temperature = 210\\nmaterial_print_temperature_layer_0 = =material
;SETTING_3 _print_temperature\\nretract_at_layer_change = True\\nretraction_amou
;SETTING_3 nt = 6.5\\nskirt_line_count = 2\\nspeed_layer_0 = =speed_print * 30 /
;SETTING_3  60\\nspeed_print = 30\\ntop_bottom_pattern = concentric\\ntop_bottom
;SETTING_3 _pattern_0 = concentric\\n\\n"]}
