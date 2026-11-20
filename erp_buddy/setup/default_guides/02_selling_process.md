---
module: Selling
keywords: selling, sales, customer, quotation, sales order, delivery note, sales invoice, payment, receivable, bán hàng, khách hàng, báo giá, đơn bán hàng, đơn hàng, giao hàng, phiếu giao hàng, hoá đơn bán, hóa đơn bán, thu tiền, công nợ phải thu
questions: làm sao để tạo đơn bán hàng | tạo SO mới | lên đơn cho khách | khách đặt hàng thì nhập vào đâu | ghi nhận đơn đặt hàng của khách | xuất bill cho khách | xuất hoá đơn cho khách hàng | quy trình bán hàng | how do I create a sales order
---
# Selling process: from customer to invoice

Standard flow: **Customer → Quotation (optional) → Sales Order → Delivery Note → Sales Invoice → Payment Entry**

## 1. Create a customer
- Go to **Selling > Customer > + Add** (/app/customer/new).
- Main fields: **Customer Name**, **Customer Type** (Company / Individual), **Customer Group**, **Territory**.
- Addresses and contacts can be added after saving.

## 2. Quotation (optional)
- Selling > Quotation > + Add. Pick the customer (Party), add item rows (Item, quantity, rate) → Save → Submit.
- When the customer accepts, use **Create > Sales Order** on the quotation.

## 3. Sales Order
- Selling > Sales Order > + Add (/app/sales-order/new).
- Required: **Customer**, **Delivery Date**, and the **Items** table (each row has Item Code, Quantity, Rate).
- Save (Draft) → review → **Submit**.

## 4. Delivery (Delivery Note)
- From a submitted Sales Order: **Create > Delivery Note**. Choose the source Warehouse → Submit. Stock goes down.

## 5. Sales Invoice
- From the Sales Order or Delivery Note: **Create > Sales Invoice** → Submit. The receivable is recorded.

## 6. Receive payment (Payment Entry)
- From the Sales Invoice: **Create > Payment** → choose the receiving account (Cash/Bank) → Submit.

## Tips
- Useful reports: **Sales Analytics**, **Accounts Receivable**, **Sales Order Analysis**.
- Submitted documents cannot be edited; cancel and amend them instead.
