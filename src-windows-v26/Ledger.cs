using Microsoft.Data.Sqlite;

namespace MintWindows;

// Private application ledger. No account, navigation, or transaction APIs.
internal sealed class Ledger
{
    readonly string connectionString = new SqliteConnectionStringBuilder {
        DataSource = Path.Combine(Program.DataRoot, "mint_wager_counter.db"), Pooling = false
    }.ToString();
    readonly SemaphoreSlim gate = new(1, 1);
    bool initialized;

    internal async Task<long> AccessAsync(string? round = null, long milli = 0)
    {
        await gate.WaitAsync();
        try
        {
            // SQLite operations do not run on the browser UI thread.
            return await Task.Run(() =>
            {
                using var db = new SqliteConnection(connectionString);
                db.Open();
                if (!initialized)
                {
                    using var create = db.CreateCommand();
                    create.CommandText = "CREATE TABLE IF NOT EXISTS rounds(round_key TEXT PRIMARY KEY,milli INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS totals(id INTEGER PRIMARY KEY,milli INTEGER NOT NULL); INSERT OR IGNORE INTO totals VALUES(1,0);";
                    create.ExecuteNonQuery(); initialized = true;
                }
                using var transaction = db.BeginTransaction();
                if (round != null)
                {
                    using var insert = db.CreateCommand(); insert.Transaction = transaction;
                    insert.CommandText = "INSERT OR IGNORE INTO rounds VALUES($key,$milli)";
                    insert.Parameters.AddWithValue("$key", "jdb-mines-9014:" + round);
                    insert.Parameters.AddWithValue("$milli", milli);
                    if (insert.ExecuteNonQuery() == 1)
                    {
                        using var update = db.CreateCommand(); update.Transaction = transaction;
                        update.CommandText = "UPDATE totals SET milli=milli+$milli WHERE id=1";
                        update.Parameters.AddWithValue("$milli", milli); update.ExecuteNonQuery();
                    }
                }
                using var read = db.CreateCommand(); read.Transaction = transaction;
                read.CommandText = "SELECT milli FROM totals WHERE id=1";
                long total = Convert.ToInt64(read.ExecuteScalar()); transaction.Commit(); return total;
            });
        }
        finally { gate.Release(); }
    }
}
