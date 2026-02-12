import sqlite3
import os
import time
from datetime import datetime

def clear_screen():
    """Clears the terminal screen based on the OS."""
    os.system('cls' if os.name == 'nt' else 'clear')

def truncate_value(val, length=20):
    """
    Truncates a value to a specific length and adds '...' if necessary.
    Handles None and non-string types gracefully.
    """
    if val is None:
        return "NULL"
    
    str_val = str(val)
    # Clean newlines for cleaner table formatting
    str_val = str_val.replace('\n', ' ').replace('\r', '')
    
    if len(str_val) > length:
        return str_val[:length-3] + "..."
    return str_val

def inspect_sqlite_db_live(db_path, table_focus=None, refresh_seconds=10):
    """
    Continuously monitors an SQLite database.
    
    Args:
        db_path (str): Path to the .db file.
        table_focus (str, optional): If provided, focuses output on this specific table
                                     and shows sample rows.
        refresh_seconds (int): How often to update the view.
    """
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at '{db_path}'")
        return

    try:
        while True:
            output = []
            
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    
                    # --- Header Info ---
                    last_updated = datetime.now().strftime("%H:%M:%S")
                    output.append(f"--- LIVE DATABASE MONITOR ---")
                    output.append(f"Target: {db_path}")
                    if table_focus:
                        output.append(f"Focus:  TABLE '{table_focus}'")
                    output.append(f"Time:   {last_updated}")
                    output.append("-" * 60)

                    # --- Mode 1: Focus on Specific Table ---
                    if table_focus:
                        # Check if table exists
                        cursor.execute("""
                            SELECT name FROM sqlite_master 
                            WHERE type='table' AND name=?
                        """, (table_focus,))
                        
                        if not cursor.fetchone():
                            output.append(f"\nError: Table '{table_focus}' not found.")
                            output.append("Available tables:")
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            for t in cursor.fetchall():
                                output.append(f" - {t[0]}")
                        else:
                            # 1. Get Metadata
                            cursor.execute(f'SELECT COUNT(*) FROM "{table_focus}"')
                            row_count = cursor.fetchone()[0]
                            
                            cursor.execute(f'PRAGMA table_info("{table_focus}")')
                            columns_info = cursor.fetchall() # list of (cid, name, type, ...)

                            # 2. Get Sample Data (2 rows)
                            cursor.execute(f'SELECT * FROM "{table_focus}" LIMIT 2')
                            samples = cursor.fetchall()
                            
                            output.append(f"Row Count: {row_count:,}")
                            output.append("")

                            # 3. Build the Master Table
                            # Columns: Name | Type | Nulls | Empty | Row 1 Sample | Row 2 Sample
                            
                            # formatting string
                            # Name(20) | Type(10) | Nulls(12) | Empty(8) | Row 1(20) | Row 2(20)
                            header_fmt = "{:<20} | {:<10} | {:<12} | {:<8} | {:<20} | {:<20}"
                            
                            output.append(header_fmt.format("Column Name", "Type", "Nulls", "Empty", "Sample 1", "Sample 2"))
                            output.append("-" * 105)

                            for idx, col in enumerate(columns_info):
                                col_name = col[1]
                                col_type = col[2]
                                
                                # -- Stats Calculation --
                                cursor.execute(f'SELECT COUNT(*) FROM "{table_focus}" WHERE "{col_name}" IS NULL')
                                null_c = cursor.fetchone()[0]
                                
                                empty_c = "-"
                                is_text = any(x in col_type.upper() for x in ['TEXT', 'CHAR', 'VARCHAR'])
                                if is_text and row_count > 0:
                                    cursor.execute(f'SELECT COUNT(*) FROM "{table_focus}" WHERE "{col_name}" = ""')
                                    empty_c = str(cursor.fetchone()[0])
                                
                                null_display = str(null_c)
                                if null_c > 0 and row_count > 0:
                                    null_display += f" ({(null_c/row_count)*100:.0f}%)"

                                # -- Sample Data Extraction --
                                # samples[0] is the first tuple of row data
                                # samples[0][idx] is the value for this column
                                sample_1_val = samples[0][idx] if len(samples) > 0 else "N/A"
                                sample_2_val = samples[1][idx] if len(samples) > 1 else "N/A"

                                output.append(header_fmt.format(
                                    truncate_value(col_name, 19),
                                    truncate_value(col_type, 10),
                                    null_display,
                                    empty_c,
                                    truncate_value(sample_1_val),
                                    truncate_value(sample_2_val)
                                ))
                            output.append("-" * 105)


                    # --- Mode 2: General Overview (No focus) ---
                    else:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                        tables = cursor.fetchall()
                        
                        output.append(f"Total Tables: {len(tables)}\n")
                        
                        # Use a simpler format for the overview
                        row_fmt = "{:<30} | {:<15} | {:<10}"
                        output.append(row_fmt.format("Table Name", "Row Count", "Columns"))
                        output.append("-" * 60)
                        
                        for (table_name,) in tables:
                            try:
                                cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                                rc = cursor.fetchone()[0]
                                cursor.execute(f'PRAGMA table_info("{table_name}")')
                                cc = len(cursor.fetchall())
                                output.append(row_fmt.format(truncate_value(table_name, 29), f"{rc:,}", str(cc)))
                            except:
                                output.append(f"{table_name:<30} | (Locked/Error)")

            except sqlite3.Error as e:
                output.append(f"\nSQLite Error: {e}")

            # Render
            clear_screen()
            print("\n".join(output))
            
            # Wait
            time.sleep(refresh_seconds)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    inspect_sqlite_db_live('data/tests.db', refresh_seconds=10)
    '''
    Table Name                     | Row Count       | Columns   
    ------------------------------------------------------------
    article_keyword_links          | 0               | 4         
    articles                       | 4,108           | 12        
    debugging                      | 3               | 12        
    keywords                       | 10,855          | 5     
    '''