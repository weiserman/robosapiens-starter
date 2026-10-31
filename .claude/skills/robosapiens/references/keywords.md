# RoboSAPiens keywords by task

For RoboSAPiens 2.36.2. The full documentation is at https://imbus.github.io/robotframework-robosapiens/RoboSAPiens.html

## From this starter

| Keyword | Use |
|---|---|
| `Open SAP Window` | Gives the test its own window on the configured system |
| `Close SAP GUI Session` | Closes that window, and logs off if the test logged on itself |
| `Get Table Rows    @{columns}` | All rows of the table on screen, as dictionaries by column title |
| `Describe Screen` | Text listing the labels, fields, buttons, tabs and table columns |
| `SAP Number    ${text}` | `1,234.50` or `12-` as a number |

## Navigating

| Keyword | Notes |
|---|---|
| `Execute Transaction    ME2N` | Add `with_command_field=True` to type it in the command field like a person |
| `Press Key Combination    F8` | Also `Enter`, `F3` (back), `Ctrl+S` |
| `Push Button    Save` | Matches part of a name or tooltip. Use `exact=True` to be strict |
| `Select Menu Entry    System/User Profile/Own Data` | `/` between levels |
| `Select Tab    Delivery` | Name or tooltip |
| `Close Window` | The foreground window, for example a popup |

## Fields

| Keyword | Notes |
|---|---|
| `Fill Text Field    Label    value` | `${EMPTY}` clears the field |
| `Read Text Field    Label` | |
| `Read Text    Label` | Text that follows a label, or `= substring` |
| `Select Radio Button    Label` | |
| `Tick Checkbox    Label` / `Untick Checkbox    Label` | |
| `Select Dropdown Menu Entry    Label    Entry` | |
| `Fill Multiline Text Field    text` | |

### Locator forms for fields

| Form | Finds |
|---|---|
| `Label` | Field with that label to its left |
| `@ Label` | Field below that label |
| `Left @ Above` | Field where the two labels meet |
| `Label @ 2` | 2nd field in a row after the label |
| `2 @ Label` | 2nd field in a column below the label |
| `Unique >> Label` | Non-unique label beside a unique one, such as `Document Date >> to` |
| `Unique >> F1 help text` | Field with no label beside a unique one |
| `S_BEDAT-HIGH` | Technical name, as `Describe Screen` shows: the last resort, since it reads badly |

Add `exact=False` to match the start of a long label.

## Tables

| Keyword | Notes |
|---|---|
| `Get Row Count` | Add `table_number=2` where a window has several |
| `Read Cell    1    Column` | By row number, from 1 |
| `Read Cell    4500000001 @ Purchasing Document    Item` | By the content of another cell in the row |
| `Fill Cell    1    Column    value` | Changes the document if saved |
| `Double-click Cell    1    Column` | Opens the row's detail in many lists |
| `Select Table Row    1` / `Select Cell    1    Column` | |
| `Tick Checkbox Cell    1    Column` | |
| `Push Button Cell    1    Column` | |

## Trees

| Keyword | Notes |
|---|---|
| `Select Tree Element    Folder/Item` | `/` between levels |
| `Expand Tree Folder    Folder/Sub` | |
| `Double-click Tree Element    Folder/Item` | |
| `Read Tree Element    Folder/Item` | |

## Reading the result

| Keyword | Notes |
|---|---|
| `Read Statusbar` | Dictionary with `status` and `message` |
| `Get Window Title` | Tells you when a popup has appeared |
| `Get Window Text` | The message in a popup |
| `Save Screenshot    LOG` | Puts the window in the log |
