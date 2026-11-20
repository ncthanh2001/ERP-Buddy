---
module: Stock
keywords: item, stock, warehouse, stock entry, material receipt, material issue, transfer, stock reconciliation, inventory, hàng hoá, hàng hóa, mặt hàng, sản phẩm, kho, nhập kho, xuất kho, chuyển kho, phiếu nhập kho, phiếu xuất kho, kiểm kê, tồn kho, đơn vị tính
questions: cách tạo phiếu nhập kho | hướng dẫn nhập kho | xuất kho dùng nội bộ | chuyển hàng giữa các kho | xem tồn kho ở đâu | tạo mặt hàng mới | kiểm kê kho | how do I receive stock into a warehouse
---
# Items and stock management

## Create an item
- Stock > Item > + Add (/app/item/new).
- Main fields: **Item Code**, **Item Name**, **Item Group**, **Default Unit of Measure** (e.g. Nos, Kg).
- **Maintain Stock**: on for physical goods, off for services.
- Selling and buying prices are set through **Item Price**.

## Warehouses
- Stock > Warehouse. Each company has a warehouse tree (e.g. Stores, Finished Goods).

## Receipts, issues and transfers (Stock Entry)
- Stock > Stock Entry > + Add, then choose the **Stock Entry Type**:
  - **Material Receipt**: bring stock in without a purchase.
  - **Material Issue**: take stock out for internal use.
  - **Material Transfer**: move stock between warehouses.
- Add item rows, source/target warehouses and quantities → Submit.

## Stock count (Stock Reconciliation)
- Adjusts stock to the physically counted quantity, or loads opening stock.

## Reports
- **Stock Balance** (stock per warehouse), **Stock Ledger**, **Stock Projected Qty**.
