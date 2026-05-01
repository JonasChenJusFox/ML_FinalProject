# NearBite Full App Function Test

This document provides instructions and 25 test accounts for validating personalization, search functionality, and overall app stability. 

## Ready-to-use test accounts

All username in the format: `test_user_##`

All accounts use the password: **`test1234`**

| # | Email | Password | Persona | Expected Homepage Behavior | Suggested Queries |
|---|---|---|---|---|---|
| 1 | `test_user_01@nearbite.test` | `test1234` | Cheap casual Asian food | Asian, affordable, casual spots | `cheap ramen near NYU`, `spicy noodles` |
| 2 | `test_user_02@nearbite.test` | `test1234` | Vegan healthy food | Vegan, Med/Middle Eastern | `vegan food near NYU`, `vegetarian food` |
| 3 | `test_user_03@nearbite.test` | `test1234` | Date night Italian | Upscale Italian, cozy/romantic | `date night restaurant`, `Italian dinner` |
| 4 | `test_user_04@nearbite.test` | `test1234` | Coffee/brunch | Cafes, brunch spots, bakeries | `cozy brunch`, `coffee and dessert` |
| 5 | `test_user_05@nearbite.test` | `test1234` | Spicy food | Indian, Thai, Mexican, lively | `spicy noodles`, `quick lunch` |
| 6 | `test_user_06@nearbite.test` | `test1234` | Dessert/cafe | Desserts, late-night sweet spots | `coffee and dessert` |
| 7 | `test_user_07@nearbite.test` | `test1234` | Mediterranean | Mediterranean, casual dining | `vegetarian food`, `quick lunch` |
| 8 | `test_user_08@nearbite.test` | `test1234` | Fast lunch near NYU | Grab-and-go, cheap, nearby | `quick lunch`, `cheap ramen near NYU` |
| 9 | `test_user_09@nearbite.test` | `test1234` | Upscale high-rated dinner | Fine dining, expensive, date night | `date night restaurant`, `vegan steakhouse near NYU` |
| 10| `test_user_10@nearbite.test` | `test1234` | No strong preference baseline | General popular restaurants | `random nonsense query`, `quick lunch` |
| 11| `test_user_11@nearbite.test` | `test1234` | Thai food | Thai, spicy, lively | `spicy noodles`, `quick lunch` |
| 12| `test_user_12@nearbite.test` | `test1234` | Korean food | K-BBQ, late-night, spicy | `spicy noodles`, `late night food` |
| 13| `test_user_13@nearbite.test` | `test1234` | Chinese food | Chinese, dim sum, groups | `spicy noodles`, `cheap ramen near NYU` |
| 14| `test_user_14@nearbite.test` | `test1234` | Japanese ramen/sushi | Sushi, ramen, cozy, upscale | `cheap ramen near NYU`, `date night restaurant` |
| 15| `test_user_15@nearbite.test` | `test1234` | Vegetarian | Veg-friendly, Indian, Mexican | `vegetarian food`, `vegan food near NYU` |
| 16| `test_user_16@nearbite.test` | `test1234` | Burger/comfort food | Burgers, American, late-night | `quick lunch`, `cheap food` |
| 17| `test_user_17@nearbite.test` | `test1234` | Mexican/taco | Tacos, casual, lively, cheap | `quick lunch`, `spicy food` |
| 18| `test_user_18@nearbite.test` | `test1234` | Indian food | Indian, cozy, spicy | `vegetarian food`, `spicy noodles` |
| 19| `test_user_19@nearbite.test` | `test1234` | Pizza/pasta | Italian, casual hangout | `Italian dinner`, `quick lunch` |
| 20| `test_user_20@nearbite.test` | `test1234` | Cheap student | Cheap, late-night, fast | `cheap ramen near NYU`, `quick lunch` |
| 21| `test_user_21@nearbite.test` | `test1234` | Trendy aesthetic cafe | Aesthetic, brunch, desserts | `cozy brunch`, `coffee and dessert` |
| 22| `test_user_22@nearbite.test` | `test1234` | Quiet study spot | Quiet, coffee, casual | `coffee and dessert`, `quick lunch` |
| 23| `test_user_23@nearbite.test` | `test1234` | Group dinner | Group-friendly, lively, Mexican/Korean | `Italian dinner`, `spicy noodles` |
| 24| `test_user_24@nearbite.test` | `test1234` | Late-night food | Late-night, fast, burgers/tacos | `cheap ramen near NYU`, `spicy noodles` |
| 25| `test_user_25@nearbite.test` | `test1234` | Mixed adventurous | Very adventurous, travels far, high ratings | `vegan steakhouse near NYU`, `random nonsense query` |

*(Note: The username format for login is just the prefix of the email, e.g., `test_user_01`)*

---

## Testing instructions

For each tester:
1. **Log in** using one assigned account from the table above.
2. **Check the homepage recommendations**. Do the fallback/initial recommendations roughly align with your persona? 
3. **Run suggested queries** in the Discover/Search tab.
4. **Like/save 3–5 restaurants** that explicitly match your persona (using the heart/save icons).
5. **Refresh the homepage** (or trigger a new blank search).
6. **Check whether results shift** toward your liked/saved behavior.

---

## Shared queries

Copy and paste these queries to test edge cases, strict routing, and semantic robustness:

- `vegan food near NYU`
- `cheap ramen near NYU`
- `date night restaurant`
- `quick lunch`
- `cozy brunch`
- `spicy noodles`
- `Italian dinner`
- `coffee and dessert`
- `vegetarian food`
- `vegan steakhouse near NYU`
- `random nonsense query`

---

## Pass/fail checks

### ✅ Pass
- The homepage recommendations roughly match the user's base profile.
- Search results accurately respond to explicit keywords (e.g., searching "vegan" actually yields vegan places).
- Interactions (likes/saves) slightly push similar restaurants higher up the ranking pool.
- Dietary restrictions and distance influence the ranking visibly.
- The app gracefully handles strict filters and does not return empty results unless truly impossible.

### ❌ Fail
- Login is broken or throws an error.
- The homepage looks identical for all 25 distinct accounts.
- Interactions do not persist upon a page refresh.
- Queries regularly return very few or completely empty results due to broken filters.
- Buttons or map pins are unresponsive.