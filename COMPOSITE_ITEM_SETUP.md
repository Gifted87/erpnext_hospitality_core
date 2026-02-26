# Composite Item Recipe System - Installation & Testing Guide

## Installation Steps

### 1. Migrate Database

Run the following command to create the new DocTypes:

```bash
cd /home/erpnext/frappe-bench
bench --site [your-site-name] migrate
```

### 2. Create Custom Fields

Run this in bench console:

```bash
bench --site [your-site-name] console
```

Then execute:

```python
from hospitality_core.setup.composite_item_setup import setup_composite_item_fields
setup_composite_item_fields()
exit()
```

### 3. Clear Cache

```bash
bench --site [your-site-name] clear-cache
bench --site [your-site-name] clear-website-cache
```

### 4. Restart Bench

```bash
bench restart
```

---

## Testing with "Fried Yam" Example

### Step 1: Create Ingredient Items

1. **Create "Yam" Item:**
   - Go to **Stock > Item > New**
   - Item Code: `YAM`
   - Item Name: `Yam`
   - Stock UOM: `Portion`
   - Is Stock Item: ✓
   - Save

2. **Create "Egg" Item:**
   - Item Code: `EGG`
   - Item Name: `Egg`
   - Stock UOM: `Nos`
   - Is Stock Item: ✓
   - Save

### Step 2: Create Composite Item

1. **Create "Fried Yam" Item:**
   - Item Code: `FRIED-YAM`
   - Item Name: `Fried Yam`
   - Stock UOM: `Portion`
   - **Is Stock Item: ✗** (IMPORTANT!)
   - **Is Composite Item: ✓** (NEW FIELD!)
   - Save

### Step 3: Create Recipe

1. Go to **Hospitality Core > Item Recipe > New**
2. Select **Composite Item:** `Fried Yam`
3. **Quantity Produced:** `1`
4. **UOM:** `Portion`
5. **Is Active:** ✓

6. Add Ingredients:
   
   | Ingredient Item | Quantity | UOM |
   |-----------------|----------|-----|
   | Yam | 1 | Portion |
   | Egg | 2 | Nos |

7. **Save** - This will automatically create a BOM

### Step 4: Add Stock for Ingredients

Create a Stock Entry to add initial stock:

1. **Stock Entry Type:** Material Receipt
2. **Target Warehouse:** Main Store
3. Add Items:
   - Yam: 10 Portions
   - Egg: 20 Nos
4. Submit

### Step 5: Check Available to Make

Open the Fried Yam item and check availability:

```python
# In bench console:
from hospitality_core.api.composite_item_utils import get_available_to_make

result = get_available_to_make("FRIED-YAM", "Main Store - YourCompany")
print(result)
```

**Expected Output:**
```python
{
    'qty': 10,  # Limited by eggs: 20÷2=10
    'ingredients': [
        {'ingredient': 'YAM', 'required_per_unit': 1.0, 'available': 10.0, 'can_make': 10},
        {'ingredient': 'EGG', 'required_per_unit': 2.0, 'available': 20.0, 'can_make': 10}
    ],
    'message': 'Success'
}
```

### Step 6: Test Sales via POS

1. **Create POS Invoice:**
   - Customer: Any customer
   - Add Item: **Fried Yam** (Qty: 2)
   - Warehouse: Main Store
   - **Submit**

2. **Check Stock Entries:**
   - Go to **Stock > Stock Ledger**
   - Filter by Item: `YAM` and `EGG`
   - You should see Material Consumption entries:
     - Yam: -2 Portions
     - Egg: -4 Nos

3. **Verify Remaining Stock:**
   - Yam: 8 Portions (10 - 2)
   - Egg: 16 Nos (20 - 4)

### Step 7: Test Cancellation

1. Cancel the POS Invoice
2. Check Stock Ledger again - consumption should be reversed
3. Verify stock is back to original:
   - Yam: 10 Portions
   - Egg: 20 Nos

---

## Verification Checklist

- [ ] Custom field `is_composite_item` appears on Item form
- [ ] Item Recipe DocType is accessible
- [ ] BOM is auto-created when saving Item Recipe
- [ ] `get_available_to_make` returns correct quantities
- [ ] Selling composite item creates Stock Entry (Material Consumption)
- [ ] Correct ingredient quantities are deducted
- [ ] Cancelling invoice reverses stock deduction
- [ ] Error shown when insufficient ingredients
- [ ] Multi-level recipes work (recipe within recipe)

---

## Troubleshooting

### Issue: "No module named hospitality_core.api.composite_item_utils"

**Solution:** Restart bench and clear cache:
```bash
bench restart
bench --site [site] clear-cache
```

### Issue: "is_composite_item" field not showing

**Solution:** Run the custom field setup again:
```bash
bench --site [site] console
from hospitality_core.setup.composite_item_setup import setup_composite_item_fields
setup_composite_item_fields()
```

### Issue: Stock Entry not created on POS Invoice submission

**Solution:** Check error log and ensure:
1. Item is marked as composite
2. Active recipe exists
3. Sufficient ingredient stock available
4. Warehouse is specified in invoice

---

## Next Steps

After successful testing:

1. Create recipes for all your composite items
2. Train staff on the system
3. Monitor stock consumption patterns
4. Consider implementing cost analysis features
