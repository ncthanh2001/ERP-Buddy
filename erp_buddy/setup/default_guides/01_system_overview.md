---
keywords: overview, modules, features, navigation, draft, submit, cancel, amend, tổng quan, phân hệ, chức năng, tính năng, điều hướng, nháp, hủy, hoá đơn, chứng từ
questions: phần mềm có những chức năng gì | hệ thống gồm những phân hệ nào | ERPNext gồm những phân hệ nào | submit chứng từ là gì | cách hủy chứng từ đã submit | what can ERPNext do
---
# ERP system overview and main modules

The ERP system is made of modules. Each module groups related screens, documents and reports:

| Module | Used for | Typical documents |
|---|---|---|
| Selling | Quotations, sales orders, customers | Customer, Quotation, Sales Order |
| Buying | Purchase requests, purchase orders, suppliers | Supplier, Material Request, Purchase Order |
| Stock | Items, receipts and issues, inventory | Item, Warehouse, Stock Entry, Delivery Note, Purchase Receipt |
| Accounts | Invoices, payments, ledgers | Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry |
| CRM | Leads and opportunities | Lead, Opportunity |
| Projects | Projects, tasks, timesheets | Project, Task, Timesheet |
| Manufacturing | Bills of materials, work orders | BOM, Work Order |
| Assets | Fixed assets and depreciation | Asset |

## Basic concepts
- **Draft → Submit → Cancel**: transactions (orders, invoices) are created as a **Draft**, then **Submitted** to post them. A submitted document cannot be edited; **Cancel** it and **Amend** it to create a corrected copy.
- **Masters**: Customer, Supplier, Item, Warehouse... are never submitted.
- **Permissions**: each user only sees the modules and documents their roles allow.

## Navigation
- Use the search bar at the top (shortcut Ctrl+G) and type a document name, e.g. "Sales Order".
- In a list, press **+ Add** to create a new record.
- The **Create** button on a document makes the next document in the flow (for example a Delivery Note or Sales Invoice from a Sales Order).
