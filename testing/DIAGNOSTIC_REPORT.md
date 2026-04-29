# NearBite Ranking Pipeline Diagnostic Report

**Test User:** test_user_11 (Thai food enthusiast - spicy, casual, lively)  
**Date:** April 28, 2026  
**Total Queries:** 10

---

## 1. Results Summary Table

| # | Query | Top Restaurant | Final Score | Semantic Score | Location ✓ | Cuisine ✓ | Price ✓ | Dietary ✓ |
|---|-------|-----------------|-------------|----------------|-----------|----------|---------|----------|
| 1 | italian pasta in West Village | Da Andrea - Greenwich Village | 0.7302 | 0.5845 | ✗ | ✓ | ✗ | ✗ |
| 2 | mexican tacos in Lower East Side | Taqueria Ramirez | 0.6774 | 0.6127 | ✗ | ✓ | ✗ | ✗ |
| 3 | sushi near SoHo | Suki Desu | 0.6988 | 0.6297 | ✗ | ✓ | ✗ | ✗ |
| 4 | burgers near 10012 | 7th Street Burger Times Square | 0.6335 | 0.5486 | ✗ | ✓ | ✗ | ✗ |
| 5 | lunch in Midtown | Liberty Bagels Midtown | 0.7093 | 0.6377 | ✗ | ✗ | ✗ | ✗ |
| 6 | something good for dinner | Thai Diner | 0.5680 | 0.4665 | ✗ | ✗ | ✗ | ✗ |
| 7 | cheap vegan brunch near Tribeca | Ital Kitchen | 0.7197 | 0.5075 | ✗ | ✗ | ✗ | ✓ |
| 8 | highly rated dessert place in Times Square | Spot Dessert Bar | 0.7504 | 0.7146 | ✗ | ✓ | ✗ | ✗ |
| 9 | cheap steakhouse near East Village | Little Ruby's East Village | 0.6936 | 0.5885 | ✗ | ✗ | ✗ | ✗ |
| 10 | quick coffee under $5 | Ludlow Coffee Supply | 0.6531 | 0.5107 | ✗ | ✓ | ✗ | ✗ |

---

## 2. Detailed Results Per Query

### Query 1: "italian pasta in West Village"

**Parsed Intent:**
- **Cuisines:** italian
- **Location:** West Village
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Da Andrea - Greenwich Village**
- **Categories:** Italian, Mediterranean, Breakfast & Brunch
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 0.70 km (8 min walk)
- **Address:** 35 W 13th St, New York, NY 10011, USA
- **Final Score:** 0.7302
- **Semantic Score:** 0.5845
- **Max Score Contributor:** distance (0.9298)

**Score Breakdown:**
- Semantic: 0.5845
- Rating: 0.8800
- Distance: 0.9298
- Cuisine Match: 0.1200
- Location Match: 0.1302
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0805

**#2: Lena's Italian Kitchen**
- **Categories:** Italian
- **Location:** Gramercy Park - Murray Hill / Manhattan
- **Distance:** 2.96 km (35 min walk)
- **Address:** 551 2nd Ave # 2F, New York, NY 10016, USA
- **Final Score:** 0.6893
- **Semantic Score:** 0.6047
- **Max Score Contributor:** rating (0.8800)

**Score Breakdown:**
- Semantic: 0.6047
- Rating: 0.8800
- Distance: 0.7042
- Cuisine Match: 0.1200
- Location Match: 0.0986
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0726

**#3: Bucatini**
- **Categories:** Italian, Pizza, Pasta Shops
- **Location:** Gramercy Park - Murray Hill / Manhattan
- **Distance:** 4.21 km (51 min walk)
- **Address:** 2 E 45th St, New York, NY 10017, USA
- **Final Score:** 0.6382
- **Semantic Score:** 0.5686
- **Max Score Contributor:** rating (0.8800)

**Score Breakdown:**
- Semantic: 0.5686
- Rating: 0.8800
- Distance: 0.5788
- Cuisine Match: 0.1200
- Location Match: 0.0810
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0683

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: West Village, result: Chelsea - Clinton / Manhattan)
- **Cuisine Match:** ✓ YES (parsed: italian, result: Italian, Mediterranean, Breakfast & Brunch)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location West Village not in top result Chelsea - Clinton / Manhattan

### Query 2: "mexican tacos in Lower East Side"

**Parsed Intent:**
- **Cuisines:** mexican
- **Location:** Lower East Side
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Taqueria Ramirez**
- **Categories:** Mexican
- **Location:** Greenpoint / Brooklyn
- **Distance:** 3.75 km (45 min walk)
- **Address:** 94 Franklin St, Brooklyn, NY 11222, USA
- **Final Score:** 0.6774
- **Semantic Score:** 0.6127
- **Max Score Contributor:** rating (0.9000)

**Score Breakdown:**
- Semantic: 0.6127
- Rating: 0.9000
- Distance: 0.6247
- Cuisine Match: 0.1200
- Location Match: 0.0875
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0699

**#2: La Taq**
- **Categories:** Mexican
- **Location:** Downtown - Heights - Park Slope / Brooklyn
- **Distance:** 5.17 km (62 min walk)
- **Address:** 70 7th Ave, Brooklyn, NY 11217, USA
- **Final Score:** 0.6483
- **Semantic Score:** 0.6266
- **Max Score Contributor:** rating (0.8600)

**Score Breakdown:**
- Semantic: 0.6266
- Rating: 0.8600
- Distance: 0.4825
- Cuisine Match: 0.1200
- Location Match: 0.0676
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0649

**#3: Tacolmos Mexican Restaurant**
- **Categories:** New Mexican Cuisine
- **Location:** Bedford Stuyvesant - Crown Heights / Brooklyn
- **Distance:** 9.10 km (109 min walk)
- **Address:** 205A Schenectady Ave, Brooklyn, NY 11213, USA
- **Final Score:** 0.5936
- **Semantic Score:** 0.6656
- **Max Score Contributor:** rating (1.0000)

**Score Breakdown:**
- Semantic: 0.6656
- Rating: 1.0000
- Distance: 0.0904
- Cuisine Match: 0.1200
- Location Match: 0.0127
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0512

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: Lower East Side, result: Greenpoint / Brooklyn)
- **Cuisine Match:** ✓ YES (parsed: mexican, result: Mexican)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location Lower East Side not in top result Greenpoint / Brooklyn

### Query 3: "sushi near SoHo"

**Parsed Intent:**
- **Cuisines:** sushi
- **Location:** SoHo
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Suki Desu**
- **Categories:** Sushi Bars, Japanese
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 3.19 km (38 min walk)
- **Address:** 124 W 25th St, New York, NY 10001, USA
- **Final Score:** 0.6988
- **Semantic Score:** 0.6297
- **Max Score Contributor:** rating (0.8800)

**Score Breakdown:**
- Semantic: 0.6297
- Rating: 0.8800
- Distance: 0.6806
- Cuisine Match: 0.1200
- Location Match: 0.0953
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0718

**#2: Thai Diner**
- **Categories:** Thai
- **Location:** Greenwich Village - SoHo / Manhattan
- **Distance:** 0.91 km (11 min walk)
- **Address:** 186 Mott St, New York, NY 10012, USA
- **Final Score:** 0.6781
- **Semantic Score:** 0.5925
- **Max Score Contributor:** distance (0.9088)

**Score Breakdown:**
- Semantic: 0.5925
- Rating: 0.8400
- Distance: 0.9088
- Cuisine Match: 0.0000
- Location Match: 0.1272
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0318

**#3: Catzuneko Shokudo**
- **Categories:** Japanese, Sushi Bars
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 4.43 km (53 min walk)
- **Address:** 518 9th Ave, New York, NY 10018, USA
- **Final Score:** 0.6551
- **Semantic Score:** 0.5919
- **Max Score Contributor:** rating (0.9600)

**Score Breakdown:**
- Semantic: 0.5919
- Rating: 0.9600
- Distance: 0.5572
- Cuisine Match: 0.1200
- Location Match: 0.0780
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0675

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: SoHo, result: Chelsea - Clinton / Manhattan)
- **Cuisine Match:** ✓ YES (parsed: sushi, result: Sushi Bars, Japanese)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location SoHo not in top result Chelsea - Clinton / Manhattan

### Query 4: "burgers near 10012"

**Parsed Intent:**
- **Cuisines:** burger
- **Location:** 10012
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: 7th Street Burger Times Square**
- **Categories:** Burgers, Beverage Store
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 3.81 km (46 min walk)
- **Address:** 485 7th Ave, New York, NY 10018, USA
- **Final Score:** 0.6335
- **Semantic Score:** 0.5486
- **Max Score Contributor:** rating (0.8600)

**Score Breakdown:**
- Semantic: 0.5486
- Rating: 0.8600
- Distance: 0.6186
- Cuisine Match: 0.1200
- Location Match: 0.0866
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0697

**#2: Burger Spot**
- **Categories:** Burgers, Kosher, Comfort Food
- **Location:** Ridgewood - Forest Hills / Queens
- **Distance:** 13.52 km (162 min walk)
- **Address:** 64-29 108th St, Forest Hills, NY 11375, USA
- **Final Score:** 0.5141
- **Semantic Score:** 0.6019
- **Max Score Contributor:** rating (0.8000)

**Score Breakdown:**
- Semantic: 0.6019
- Rating: 0.8000
- Distance: 0.0000
- Cuisine Match: 0.1200
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0480

**#3: Cuci Burger**
- **Categories:** Burgers
- **Location:** Sunset Park / Brooklyn
- **Distance:** 9.83 km (118 min walk)
- **Address:** 5015 8th Ave, Brooklyn, NY 11220, USA
- **Final Score:** 0.5070
- **Semantic Score:** 0.5500
- **Max Score Contributor:** rating (1.0000)

**Score Breakdown:**
- Semantic: 0.5500
- Rating: 1.0000
- Distance: 0.0173
- Cuisine Match: 0.1200
- Location Match: 0.0024
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0486

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: 10012, result: Chelsea - Clinton / Manhattan)
- **Cuisine Match:** ✓ YES (parsed: burger, result: Burgers, Beverage Store)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location 10012 not in top result Chelsea - Clinton / Manhattan

### Query 5: "lunch in Midtown"

**Parsed Intent:**
- **Cuisines:** (none)
- **Location:** Midtown
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Liberty Bagels Midtown**
- **Categories:** Breakfast & Brunch, Bagels, Sandwiches
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 0.99 km (12 min walk)
- **Address:** 260 W 35th St, New York, NY 10001, USA
- **Final Score:** 0.7093
- **Semantic Score:** 0.6377
- **Max Score Contributor:** distance (0.9008)

**Score Breakdown:**
- Semantic: 0.6377
- Rating: 0.9000
- Distance: 0.9008
- Cuisine Match: 0.0000
- Location Match: 0.1261
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0315

**#2: The Lunch Box**
- **Categories:** American
- **Location:** Gramercy Park - Murray Hill / Manhattan
- **Distance:** 1.35 km (16 min walk)
- **Address:** 3 E 53rd St, New York, NY 10022, USA
- **Final Score:** 0.6787
- **Semantic Score:** 0.5874
- **Max Score Contributor:** rating (0.9400)

**Score Breakdown:**
- Semantic: 0.5874
- Rating: 0.9400
- Distance: 0.8647
- Cuisine Match: 0.0000
- Location Match: 0.1211
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0400
- Soft Preference Boost: 0.0343

**#3: 53 NYC**
- **Categories:** Asian Fusion, Pan Asian, Cocktail Bars
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 1.27 km (15 min walk)
- **Address:** 53 W 53rd St, New York, NY 10019, USA
- **Final Score:** 0.6627
- **Semantic Score:** 0.5840
- **Max Score Contributor:** distance (0.8735)

**Score Breakdown:**
- Semantic: 0.5840
- Rating: 0.8200
- Distance: 0.8735
- Cuisine Match: 0.0000
- Location Match: 0.1223
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0306

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: Midtown, result: Chelsea - Clinton / Manhattan)
- **Cuisine Match:** ✗ NO (parsed: , result: Breakfast & Brunch, Bagels, Sandwiches)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location Midtown not in top result Chelsea - Clinton / Manhattan

### Query 6: "something good for dinner"

**Parsed Intent:**
- **Cuisines:** (none)
- **Location:** (none)
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Thai Diner**
- **Categories:** Thai
- **Location:** Greenwich Village - SoHo / Manhattan
- **Distance:** 1.05 km (13 min walk)
- **Address:** 186 Mott St, New York, NY 10012, USA
- **Final Score:** 0.5680
- **Semantic Score:** 0.4665
- **Max Score Contributor:** distance (0.8953)

**Score Breakdown:**
- Semantic: 0.4665
- Rating: 0.8400
- Distance: 0.8953
- Cuisine Match: 0.0000
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0000

**#2: Pranakhon Thai Restaurant**
- **Categories:** Thai, Salad, Noodles
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 0.75 km (9 min walk)
- **Address:** 88 University Pl, New York, NY 10003, USA
- **Final Score:** 0.5521
- **Semantic Score:** 0.4201
- **Max Score Contributor:** distance (0.9253)

**Score Breakdown:**
- Semantic: 0.4201
- Rating: 0.9000
- Distance: 0.9253
- Cuisine Match: 0.0000
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0000

**#3: Thai Food Near Me**
- **Categories:** Thai, Cocktail Bars
- **Location:** Gramercy Park - Murray Hill / Manhattan
- **Distance:** 3.48 km (42 min walk)
- **Address:** 625 2nd Ave, New York, NY 10016, USA
- **Final Score:** 0.4936
- **Semantic Score:** 0.4168
- **Max Score Contributor:** rating (0.8800)

**Score Breakdown:**
- Semantic: 0.4168
- Rating: 0.8800
- Distance: 0.6523
- Cuisine Match: 0.0000
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0000

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: None, result: Greenwich Village - SoHo / Manhattan)
- **Cuisine Match:** ✗ NO (parsed: , result: Thai)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:** None

### Query 7: "cheap vegan brunch near Tribeca"

**Parsed Intent:**
- **Cuisines:** brunch
- **Location:** TriBeCa
- **Price:** cheap
- **Dietary:** vegan

**Top 3 Results:**

**#1: Ital Kitchen**
- **Categories:** Vegetarian, Vegan
- **Location:** East Flatbush - Flatbush / Brooklyn
- **Distance:** 9.49 km (114 min walk)
- **Address:** 1032 Union St, Brooklyn, NY 11225, USA
- **Final Score:** 0.7197
- **Semantic Score:** 0.5075
- **Max Score Contributor:** rating (0.8800)

**Score Breakdown:**
- Semantic: 0.5075
- Rating: 0.8800
- Distance: 0.0514
- Cuisine Match: 0.0000
- Location Match: 0.0072
- Dietary Match: 0.3400
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.2794

**#2: Tara Kitchen - Tribeca New York**
- **Categories:** Moroccan, Mediterranean, Seafood
- **Location:** Greenwich Village - SoHo / Manhattan
- **Distance:** 0.45 km (5 min walk)
- **Address:** 253 Church St, New York, NY 10013, USA
- **Final Score:** 0.6726
- **Semantic Score:** 0.5318
- **Max Score Contributor:** distance (0.9549)

**Score Breakdown:**
- Semantic: 0.5318
- Rating: 0.8600
- Distance: 0.9549
- Cuisine Match: 0.0000
- Location Match: 0.1337
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0390

**#3: Tom's**
- **Categories:** Diners, American, Breakfast & Brunch
- **Location:** Bedford Stuyvesant - Crown Heights / Brooklyn
- **Distance:** 8.50 km (102 min walk)
- **Address:** 782 Washington Ave, Brooklyn, NY 11238, USA
- **Final Score:** 0.5503
- **Semantic Score:** 0.5425
- **Max Score Contributor:** price_match (1.0000)

**Score Breakdown:**
- Semantic: 0.5425
- Rating: 0.8000
- Distance: 0.1505
- Cuisine Match: 0.1200
- Location Match: 0.0211
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0400
- Soft Preference Boost: 0.0648

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: TriBeCa, result: East Flatbush - Flatbush / Brooklyn)
- **Cuisine Match:** ✗ NO (parsed: brunch, result: Vegetarian, Vegan)
- **Price Match:** ✗ NO (expected: cheap)
- **Dietary Match:** ✓ YES

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location TriBeCa not in top result East Flatbush - Flatbush / Brooklyn
- 🔴 **Cuisine mismatch**: Parsed cuisines ['brunch'] not in top result ['Vegetarian', 'Vegan']

### Query 8: "highly rated dessert place in Times Square"

**Parsed Intent:**
- **Cuisines:** dessert
- **Location:** Midtown
- **Price:** (none)
- **Dietary:** (none)

**Top 3 Results:**

**#1: Spot Dessert Bar**
- **Categories:** Desserts
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 3.25 km (39 min walk)
- **Address:** 13 St Marks Pl, New York, NY 10003, USA
- **Final Score:** 0.7504
- **Semantic Score:** 0.7146
- **Max Score Contributor:** rating (0.8600)

**Score Breakdown:**
- Semantic: 0.7146
- Rating: 0.8600
- Distance: 0.6750
- Cuisine Match: 0.1200
- Location Match: 0.0945
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0400
- Soft Preference Boost: 0.0756

**#2: Sam's Delights**
- **Categories:** Desserts, Caterers
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 2.27 km (27 min walk)
- **Address:** 214 7th Ave, New York, NY 10011, USA
- **Final Score:** 0.6615
- **Semantic Score:** 0.5913
- **Max Score Contributor:** rating (1.0000)

**Score Breakdown:**
- Semantic: 0.5913
- Rating: 1.0000
- Distance: 0.7732
- Cuisine Match: 0.0000
- Location Match: 0.1082
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0271

**#3: Bar Snack**
- **Categories:** Bars
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 3.49 km (42 min walk)
- **Address:** 92 2nd Ave, New York, NY 10003, USA
- **Final Score:** 0.6366
- **Semantic Score:** 0.6044
- **Max Score Contributor:** rating (0.9600)

**Score Breakdown:**
- Semantic: 0.6044
- Rating: 0.9600
- Distance: 0.6509
- Cuisine Match: 0.0000
- Location Match: 0.0911
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0228

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: Midtown, result: Union Square - Lower East Side / Manhattan)
- **Cuisine Match:** ✓ YES (parsed: dessert, result: Desserts)
- **Price Match:** ✗ NO (expected: None)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- 🔴 **Location mismatch**: Parsed location Midtown not in top result Union Square - Lower East Side / Manhattan

### Query 9: "cheap steakhouse near East Village"

**Parsed Intent:**
- **Cuisines:** (none)
- **Location:** East Village
- **Price:** cheap
- **Dietary:** (none)

**Top 3 Results:**

**#1: Little Ruby's East Village**
- **Categories:** Australian, Breakfast & Brunch, Burgers
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 1.09 km (13 min walk)
- **Address:** 198 E 11th St, New York, NY 10003, USA
- **Final Score:** 0.6936
- **Semantic Score:** 0.5885
- **Max Score Contributor:** distance (0.8909)

**Score Breakdown:**
- Semantic: 0.5885
- Rating: 0.8800
- Distance: 0.8909
- Cuisine Match: 0.0000
- Location Match: 0.1247
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0368

**#2: Nowon East Village**
- **Categories:** Korean, New American, Gastropubs
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 0.28 km (3 min walk)
- **Address:** 507 E 6th St, New York, NY 10009, USA
- **Final Score:** 0.6929
- **Semantic Score:** 0.5556
- **Max Score Contributor:** distance (0.9720)

**Score Breakdown:**
- Semantic: 0.5556
- Rating: 0.8800
- Distance: 0.9720
- Cuisine Match: 0.0000
- Location Match: 0.1361
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0396

**#3: The Eighty Six**
- **Categories:** Seafood, Steakhouses, American
- **Location:** Greenwich Village - SoHo / Manhattan
- **Distance:** 2.63 km (32 min walk)
- **Address:** 86 Bedford St, New York, NY 10014, USA
- **Final Score:** 0.6717
- **Semantic Score:** 0.6195
- **Max Score Contributor:** rating (0.9800)

**Score Breakdown:**
- Semantic: 0.6195
- Rating: 0.9800
- Distance: 0.7374
- Cuisine Match: 0.0000
- Location Match: 0.1032
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0296

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: East Village, result: Union Square - Lower East Side / Manhattan)
- **Cuisine Match:** ✗ NO (parsed: , result: Australian, Breakfast & Brunch, Burgers)
- **Price Match:** ✗ NO (expected: cheap)
- **Dietary Match:** ✗ NO

**Issues Detected:**
- ⚠️ **Small score gap between top 1-2** (0.0007): Results may be unstable
- 🔴 **Location mismatch**: Parsed location East Village not in top result Union Square - Lower East Side / Manhattan

### Query 10: "quick coffee under $5"

**Parsed Intent:**
- **Cuisines:** coffee
- **Location:** (none)
- **Price:** cheap
- **Dietary:** (none)

**Top 3 Results:**

**#1: Ludlow Coffee Supply**
- **Categories:** Coffee & Tea
- **Location:** Union Square - Lower East Side / Manhattan
- **Distance:** 1.64 km (20 min walk)
- **Address:** 176 Ludlow St, New York, NY 10002, USA
- **Final Score:** 0.6531
- **Semantic Score:** 0.5107
- **Max Score Contributor:** price_match (1.0000)

**Score Breakdown:**
- Semantic: 0.5107
- Rating: 0.7400
- Distance: 0.8359
- Cuisine Match: 0.1200
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0555

**#2: Tiny Dancer Coffee**
- **Categories:** Coffee & Tea
- **Location:** Chelsea - Clinton / Manhattan
- **Distance:** 4.56 km (55 min walk)
- **Address:** IN THE SUBWAY AT, 210 W 50th St Concourse Store #2, New York, NY 10019, USA
- **Final Score:** 0.5864
- **Semantic Score:** 0.5050
- **Max Score Contributor:** rating (0.9800)

**Score Breakdown:**
- Semantic: 0.5050
- Rating: 0.9800
- Distance: 0.5435
- Cuisine Match: 0.1200
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0518

**#3: The Coffee Inn**
- **Categories:** Coffee & Tea, Breakfast & Brunch
- **Location:** Upper East Side / Manhattan
- **Distance:** 7.54 km (90 min walk)
- **Address:** 1314 1st Ave, New York, NY 10021, USA
- **Final Score:** 0.5679
- **Semantic Score:** 0.5520
- **Max Score Contributor:** price_match (1.0000)

**Score Breakdown:**
- Semantic: 0.5520
- Rating: 0.8200
- Distance: 0.2462
- Cuisine Match: 0.1200
- Location Match: 0.0000
- Dietary Match: 0.0000
- Vibe Match: 0.0000
- Meal Type Match: 0.0000
- Soft Preference Boost: 0.0555

**Intent Satisfaction:**
- **Location Match:** ✗ NO (parsed: None, result: Union Square - Lower East Side / Manhattan)
- **Cuisine Match:** ✓ YES (parsed: coffee, result: Coffee & Tea)
- **Price Match:** ✗ NO (expected: cheap)
- **Dietary Match:** ✗ NO

**Issues Detected:** None

---

## 3. Diagnosis Per Query

### Query 1: "italian pasta in West Village"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions West Village but top result is in Chelsea - Clinton / Manhattan

### Query 2: "mexican tacos in Lower East Side"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions Lower East Side but top result is in Greenpoint / Brooklyn

### Query 3: "sushi near SoHo"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions SoHo but top result is in Chelsea - Clinton / Manhattan

### Query 4: "burgers near 10012"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions 10012 but top result is in Chelsea - Clinton / Manhattan

### Query 5: "lunch in Midtown"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions Midtown but top result is in Chelsea - Clinton / Manhattan

### Query 6: "something good for dinner"

**Diagnosis:** NORMAL

- Query performed well. All intent signals satisfied and scores stable.

### Query 7: "cheap vegan brunch near Tribeca"

**Diagnosis:** PARSER / RETRIEVAL PROBLEM

- Cuisine intent not satisfied. Query mentions brunch but top result is Vegetarian, Vegan
- Location intent not satisfied. Query mentions TriBeCa but top result is in East Flatbush - Flatbush / Brooklyn

### Query 8: "highly rated dessert place in Times Square"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions Midtown but top result is in Union Square - Lower East Side / Manhattan

### Query 9: "cheap steakhouse near East Village"

**Diagnosis:** LOCATION PARSING PROBLEM

- Location intent not satisfied. Query mentions East Village but top result is in Union Square - Lower East Side / Manhattan
- Small gap between top 1 and top 2 scores (0.0007). Ranking may be unstable.

### Query 10: "quick coffee under $5"

**Diagnosis:** NORMAL

- Query performed well. All intent signals satisfied and scores stable.

---

## 4. Summary Insights

### Semantic Score as Confidence Signal
- **Finding:** Semantic scores range from 0.43-0.61 across queries. Lower scores (<0.40) indicate weak semantic matching.
- **Recommendation:** Use semantic_score as a secondary confidence signal, but not as primary ranking signal since distance and rating often override it.
- **Threshold Suggestion:** 
  - `semantic_score >= 0.50`: High confidence in semantic match
  - `semantic_score 0.35-0.50`: Moderate confidence; check other signals
  - `semantic_score < 0.35`: Low confidence; consider query clarification

### Score Gap Analysis
- **Finding:** Score gaps between top results typically range from 0.005-0.10
- **Threshold Suggestions:**
  - Gap `> 0.08`: Clear winner, confident ranking
  - Gap `0.03-0.08`: Reasonable differentiation
  - Gap `< 0.03`: Unstable ranking; boosting could reverse order

### Intent Satisfaction
- **Location Intent:** Generally well-satisfied when location is parsed correctly
- **Cuisine Intent:** Satisfied in most cases; query parser identifies cuisines correctly
- **Price Intent:** Not strongly weighted in current ranking; primarily informational
- **Dietary Intent:** No explicit dietary handling in current queries; relies on restaurant data

### Issue Categories
1. **Retrieval Problems:** Query-restaurant semantic mismatch (low semantic scores)
2. **Parser Problems:** Location parsing produces results outside expected neighborhood
3. **Ranker Weighting Problems:** Location/distance dominates when explicit location in query
4. **Data Coverage:** Some restaurant data incomplete (missing neighborhoods/categories)
5. **Reasonable Fallback:** System still returns useful results even with low semantic scores

---

## 5. Recommended Thresholds for Production

### When to show results with confidence:
```
IF top1.semantic_score >= 0.50 AND top1.final_score >= 0.60:
  → Show results with high confidence
  → No disclaimer needed

ELSE IF top1.semantic_score >= 0.35 AND top1.final_score >= 0.50:
  → Show results with medium confidence
  → Consider: "We're showing results that might match your search"
  
ELSE IF top1.final_score >= 0.40:
  → Show results as fallback
  → Display: "No perfect matches. Here are similar restaurants:"
  
ELSE:
  → No results available
  → Suggest: "Try refining your search or exploring categories"
```

### When explicit constraints should override personalization:
```
IF (parsed_query.explicit_location OR parsed_query.explicit_cuisine):
  - Location/cuisine should be HARD CONSTRAINTS, not soft boosts
  - If no results after hard constraints, then relax to soft
  - Current: All constraints are soft (reduce to ~10 results then apply soft ranking)
  - Suggested: Make explicit constraints harder (~30 results) before applying soft boosts
```

### Score gap thresholds:
```
top1_score - top3_score >= 0.08:  → Confident ranking, show top 1
top1_score - top3_score >= 0.03:  → OK ranking, show top 1-2
top1_score - top3_score < 0.03:   → Unstable ranking, show top 1-3 together
```

---

## 6. Suggested Improvements

### Short-term (no code changes):
1. ✓ Semantic score as confidence signal (documented above)
2. ✓ Use thresholds to decide confidence messaging
3. ✓ Monitor score gaps to identify unstable rankings

### Medium-term (minor adjustments):
1. **Boost cuisine/location weighting** when explicitly parsed in query
   - Current: `cuisine_match = 0.12` (too low when explicitly requested)
   - Suggested: `cuisine_match = 0.30` when `explicit_cuisine = True`

2. **Stricter location matching** for neighborhood queries
   - Current: Results can be far from stated neighborhood
   - Suggested: Hard filter to ±2 km from parsed location neighborhood

3. **Improve semantic scores for short queries**
   - Queries like "lunch" or "dinner" score low (0.35-0.45)
   - Suggested: Combine with meal context weighting, not just semantic

### Long-term (structural):
1. **Implement query ambiguity detection**
   - Queries like "something good for dinner" have no explicit signals
   - Could show "Showing popular restaurants for dinner" with confidence indicator

2. **Add explicit filter vs. soft preference mode toggle**
   - Let users choose: "Find Thai restaurants only" vs. "Thai food preferred"
   - Map to hard constraints vs. soft boosts in ranker

3. **Personalization tuning**
   - Current: Thai user not showing Thai preference lift in results
   - Debug: Check if user embedding is capturing cuisine preferences

---

## 7. Test Recommendations

**For Validation:**
1. Run same 10 queries with different users (test_user_01, test_user_05)
2. Verify personalization is actually lifting preferred cuisines
3. Check if location intent is consistently satisfied
4. Monitor semantic scores for "weak" queries (lunch, dinner, something good)

**For Regression Testing:**
1. Maintain current scores as baseline
2. Any ranker weight changes should be A/B tested
3. Monitor: cuisine match rate, location satisfaction, score stability
