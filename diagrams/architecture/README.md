# Architecture Diagrams — PlantUML Source

This folder contains PlantUML source files for every service in the
BookStore microservices system.

## Files

| File | Diagram |
|------|---------|
| `00_overview.puml`               | Full system overview (all 12 services) |
| `01_api_gateway.puml`            | API Gateway routing and proxy |
| `02_customer_service.puml`       | Customer Service + cart auto-creation |
| `03_book_service.puml`           | Book Service + staff book management |
| `04_cart_service.puml`           | Cart Service + book validation flow |
| `05_order_service.puml`          | Order Service + payment/ship orchestration |
| `06_pay_service.puml`            | Payment Service |
| `07_ship_service.puml`           | Shipment Service |
| `08_comment_rate_service.puml`   | Comment & Rate Service |
| `09_staff_service.puml`          | Staff Service |
| `10_manager_service.puml`        | Manager Service |
| `11_catalog_service.puml`        | Catalog Service |
| `12_recommender_ai_service.puml` | Recommender AI Service |

---

## How to Render (PNG / SVG)

### Option A — VS Code Extension (recommended)
1. Install **PlantUML** extension by `jebbs` in VS Code.
2. Open any `.puml` file.
3. Press `Alt+D` to preview, or `Ctrl+Shift+P` → **PlantUML: Export Current Diagram**.
4. Choose PNG or SVG output.

> Requires Java and either a local PlantUML jar or the online server.

### Option B — Command Line (local jar)
```bash
# Download plantuml.jar from https://plantuml.com/download
# Then run:
java -jar plantuml.jar diagrams/architecture/*.puml -o rendered/
```

### Option C — Online (no install)
1. Open https://www.plantuml.com/plantuml/uml/
2. Paste the contents of any `.puml` file.
3. Download the PNG.

### Option D — All at once (PowerShell, jar in PATH)
```powershell
Get-ChildItem diagrams\architecture\*.puml | ForEach-Object {
    java -jar plantuml.jar $_.FullName -o ..\..\diagrams\architecture\rendered\
}
```

---

## After Rendering
Place the exported PNG files in `diagrams/architecture/rendered/` and
insert them into the relevant placeholder boxes in the DOCX report.
