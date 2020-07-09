#!/usr/bin/env python

import transformations
import gps_util
import numpy as np

anchor_lat = 38.432147 # 38.431960
anchor_long = -78.876115 # -78.875910
anchor_elev = 396 #meters above sea level
anchor_theta = 0 #angle pointing directly north, originally: 0


#X
v0 = [[35.9750671387,
14.0169754028,
-3.60410761833,
17.4223442078,
30.7783546448,
59.0794563293,
47.9315681458],
#Y
[36.4229431152,
1.30921435356,
8.7294960022,
46.9932327271,
43.7685050964,
72.0065460205,
86.720085144]] 





#Latitude
v1 = [[38.431686,
38.432053,
38.432108,
38.431724,
38.431672,
38.431312,
38.431282],
#Longitude
[-78.876137,
-78.876221,
-78.876016,
-78.875895,
-78.876047,
-78.876070,
-78.875866]]

affine = transformations.affine_matrix_from_points(v0, v1)
# print(affine)

'''#!/usr/bin/env python

import transformations

#X
v0 = [[36.4229431152,
1.30921435356,
8.7294960022,
46.9932327271,
43.7685050964,
72.0065460205,
86.720085144], 
#Y
[35.9750671387,
14.0169754028,
-3.60410761833,
17.4223442078,
30.7783546448,
59.0794563293,
47.9315681458]] 



#Latitude
v1 = [[-78.876137,
-78.876221,
-78.876016,
-78.875895,
-78.876047,
-78.876070,
-78.875866],
#Longitude
[38.431686,
38.432053,
38.432108,
38.431724,
38.431672,
38.431312,
38.431282]]




affine = transformations.affine_matrix_from_points(v0, v1)
print(affine)
'''
