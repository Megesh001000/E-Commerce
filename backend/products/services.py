from django.db import transaction
from .models import Product,StockAdjustment

@transaction.atomic()
def adjust_product_stock(product_id,quantity_change,reason,adjusted_by=None,note=""):

    if quantity_change==0: #validate quantity
        raise ValueError("Stock adjustment cannot be zero.")

    if reason not in StockAdjustment.Reason.values:  #validate adjustment reason
        raise ValueError("Invalid stock adjustment reason.")


    #validate adjustment direction
    if reason  in [StockAdjustment.Reason.RETURN,StockAdjustment.Reason.RESTOCK] and  quantity_change <0:
        raise ValueError(
            "This adjustment reason requires a positive quantity."
        )

    if (reason==StockAdjustment.Reason.DAMAGED and quantity_change>0):
        raise ValueError(
            "Damaged stock must have a negative quantity."
        )
    product=Product.objects.select_for_update().get(pk=product_id)
    previous_stock=product.stock
    new_stock=previous_stock+quantity_change

    if new_stock<0: #prevent negative stock
        raise ValueError("Insufficient stock for this adjustment.")

    product.stock=new_stock  #updare stock

    product.save(
        update_fields=[
            "stock",
            "updated_at",
        ]
    )

    #record adjustments
    adjustment=StockAdjustment.objects.create(
        product=product,
        adjusted_by=adjusted_by,
        quantity_change=quantity_change,
        previous_stock=previous_stock,
        new_stock=new_stock,
        reason=reason,
        note=note,

    )
    return adjustment