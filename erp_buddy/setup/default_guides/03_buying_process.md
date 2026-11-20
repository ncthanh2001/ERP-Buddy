---
module: Buying
keywords: buying, purchase, supplier, material request, purchase order, purchase receipt, purchase invoice, payable, mua hàng, nhà cung cấp, yêu cầu vật tư, đơn mua hàng, đặt hàng nhà cung cấp, nhận hàng, phiếu nhập mua, hoá đơn mua, hóa đơn mua, trả tiền, công nợ phải trả
questions: quy trình mua hàng | tạo đơn mua hàng | đặt hàng với nhà cung cấp | tạo PO mới | nhận hàng từ nhà cung cấp | thanh toán cho nhà cung cấp | how do I create a purchase order
---
# Buying process

Standard flow: **Supplier → Material Request (optional) → Purchase Order → Purchase Receipt → Purchase Invoice → Payment Entry**

## 1. Supplier
- Buying > Supplier > + Add (/app/supplier/new). Main fields: **Supplier Name**, **Supplier Group**, **Supplier Type**.

## 2. Material Request (optional)
- The department that needs goods raises a request: type **Purchase**, add items, quantities and the required date.

## 3. Purchase Order
- Buying > Purchase Order > + Add. Required: **Supplier**, **Required By** date, and the **Items** table (Item Code, Quantity, Rate).
- Save → Submit.

## 4. Receive goods (Purchase Receipt)
- From the Purchase Order: **Create > Purchase Receipt**, choose the Accepted Warehouse → Submit. Stock goes up.

## 5. Purchase Invoice and payment
- **Create > Purchase Invoice** → Submit (records the payable) → **Create > Payment** to pay the supplier.

## Useful reports
- **Purchase Analytics**, **Accounts Payable**, **Purchase Order Analysis**.
