using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Mintada.Navigator.Models;
using System.IO;

namespace Mintada.Navigator.Services
{
    public class DatabaseService
    {
        private readonly string _connectionString;

        public DatabaseService(string dbPath)
        {
            _connectionString = $"Data Source={dbPath}";
        }

        public string GetDbPath() 
        {
            // Extract path from connection string "Data Source=..."
            if (_connectionString.StartsWith("Data Source="))
                return _connectionString.Substring("Data Source=".Length);
            return _connectionString;
        }

        public async Task<List<Issuer>> GetIssuersAsync()
        {
            var issuers = new List<Issuer>();

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();

                var command = connection.CreateCommand();
                command.CommandText = 
                    @"SELECT id, numista_name, numista_url_slug, numista_parent_url_slug, numista_territory_type 
                      FROM issuers 
                      ORDER BY numista_name";

                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        issuers.Add(new Issuer
                        {
                            Id = reader.GetInt64(0),
                            Name = reader.GetString(1),
                            UrlSlug = reader.GetString(2),
                            ParentUrlSlug = reader.IsDBNull(3) ? null : reader.GetString(3),
                            TerritoryType = reader.IsDBNull(4) ? "" : reader.GetString(4)
                        });
                    }
                }
            }

            return issuers;
        }

        public async Task<long?> GetIssuerIdByCoinTypeIdAsync(long coinTypeId)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = "SELECT issuer_id FROM coin_types WHERE id = @id";
                command.Parameters.AddWithValue("@id", coinTypeId);
                
                var result = await command.ExecuteScalarAsync();
                if (result != null && result != DBNull.Value)
                {
                    return Convert.ToInt64(result);
                }
            }
            return null;
        }

        public async Task<List<CoinType>> GetCoinTypesAsync(long issuerId, string issuerSlug)
        {
            var coins = new List<CoinType>();

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();

                var command = connection.CreateCommand();
                command.CommandText = 
                    @"SELECT ct.id, ct.title, cts.obverse_image, cts.reverse_image, cts.sample_type, 
                             ct.subtitle, ct.coin_type_slug, ct.period, ct.fixed, cts.is_holder, 
                             cts.is_counterstamped, cts.is_roll, cts.contains_holder, cts.contains_text, cts.is_multi_coin,
                             ct.shape_id, ct.shape_info, ct.weight_info, ct.diameter_info, ct.thickness_info,
                             ct.weight, ct.diameter, ct.thickness, ct.size,
                             ct.denomination_text, ct.value_amount, ct.denomination_info_1, ct.value_amount_usd, ct.value_currency_symbol, ct.denomination_alt,
                             ct.start_date, ct.end_date, ct.start_native_date, ct.end_native_date, ct.start_mint_date, ct.end_mint_date,
                             ct.restrike_date, ct.restrike_start_mint_date, ct.restrike_end_mint_date,
                             ct.erroneous_dates,
                             ct.calendar_system_id,
                             ct.period_id
                      FROM coin_types ct
                      LEFT JOIN coin_type_samples cts ON ct.id = cts.coin_type_id AND (cts.removed IS NULL OR cts.removed = 0)
                      WHERE ct.issuer_id = $issuerId 
                      ORDER BY ct.title, cts.sample_type"; 
                
                command.Parameters.AddWithValue("$issuerId", issuerId);

                // Use a dictionary to aggregate samples for the same coin
                var coinDict = new Dictionary<long, CoinType>();

                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        long coinId = reader.GetInt64(0);
                        
                        if (!coinDict.TryGetValue(coinId, out var coin))
                        {
                            coin = new CoinType
                            {
                                Id = coinId,
                                IssuerId = issuerId,
                                Title = reader.GetString(1),
                                Subtitle = reader.IsDBNull(5) ? null : reader.GetString(5),
                                CoinTypeSlug = reader.GetString(6),
                                Period = reader.IsDBNull(7) ? null : reader.GetString(7),
                                IsFixed = !reader.IsDBNull(8) && reader.GetBoolean(8),
                                ShapeId = !reader.IsDBNull(15) ? reader.GetInt32(15) : (int?)null,
                                ShapeInfo = !reader.IsDBNull(16) ? reader.GetString(16) : null,
                                WeightInfo = !reader.IsDBNull(17) ? reader.GetString(17) : null,
                                DiameterInfo = !reader.IsDBNull(18) ? reader.GetString(18) : null,
                                ThicknessInfo = !reader.IsDBNull(19) ? reader.GetString(19) : null,
                                Weight = !reader.IsDBNull(20) ? reader.GetDecimal(20) : null,
                                Diameter = !reader.IsDBNull(21) ? reader.GetDecimal(21) : null,
                                Thickness = !reader.IsDBNull(22) ? reader.GetDecimal(22) : null,
                                Size = !reader.IsDBNull(23) ? reader.GetString(23) : null,
                                DenominationText = !reader.IsDBNull(24) ? reader.GetString(24) : null,
                                ValueAmount = !reader.IsDBNull(25) ? reader.GetDecimal(25) : null,
                                DenominationInfo1 = !reader.IsDBNull(26) ? reader.GetString(26) : null,
                                ValueAmountUsd = !reader.IsDBNull(27) ? reader.GetDecimal(27) : null,
                                ValueCurrencySymbol = !reader.IsDBNull(28) ? reader.GetString(28) : null,
                                DenominationAlt = !reader.IsDBNull(29) ? reader.GetString(29) : null,
                                StartDate = !reader.IsDBNull(30) ? reader.GetString(30) : null,
                                EndDate = !reader.IsDBNull(31) ? reader.GetString(31) : null,
                                StartNativeDate = !reader.IsDBNull(32) ? reader.GetString(32) : null,
                                EndNativeDate = !reader.IsDBNull(33) ? reader.GetString(33) : null,
                                StartMintDate = !reader.IsDBNull(34) ? reader.GetString(34) : null,
                                EndMintDate = !reader.IsDBNull(35) ? reader.GetString(35) : null,
                                RestrikeDate = !reader.IsDBNull(36) ? reader.GetString(36) : null,
                                RestrikeStartMintDate = !reader.IsDBNull(37) ? reader.GetString(37) : null,
                                RestrikeEndMintDate = !reader.IsDBNull(38) ? reader.GetString(38) : null,
                                ErroneousDates = !reader.IsDBNull(39) ? reader.GetString(39) : null,
                                CalendarSystemId = !reader.IsDBNull(40) ? reader.GetInt32(40) : (int?)null,
                                PeriodId = !reader.IsDBNull(41) ? reader.GetInt32(41) : (int?)null,
                                IssuerUrlSlug = issuerSlug
                            };
                            coinDict[coinId] = coin;
                            coins.Add(coin);
                        }

                        bool hasObv = !reader.IsDBNull(2);
                        bool hasRev = !reader.IsDBNull(3);

                        if (hasObv || hasRev)
                        {
                            string? obv = hasObv ? reader.GetString(2) : null;
                            string? rev = hasRev ? reader.GetString(3) : null;
                            int type = reader.GetInt32(4);
                            bool isHolder = !reader.IsDBNull(9) && reader.GetBoolean(9);
                            bool isCounterstamped = !reader.IsDBNull(10) && reader.GetBoolean(10);
                            bool isRoll = !reader.IsDBNull(11) && reader.GetBoolean(11);
                            bool containsHolder = !reader.IsDBNull(12) && reader.GetBoolean(12);
                            bool containsText = !reader.IsDBNull(13) && reader.GetBoolean(13);
                            bool isMultiCoin = !reader.IsDBNull(14) && reader.GetBoolean(14);
                            coin.Samples.Add(new CoinSample(obv, rev, type) 
                            { 
                                IsHolder = isHolder,
                                IsCounterstamped = isCounterstamped,
                                IsRoll = isRoll,
                                ContainsHolder = containsHolder,
                                ContainsText = containsText,
                                IsMultiCoin = isMultiCoin
                            });
                        }
                    }
                }
            }

            return coins;
        }
    public async Task<HashSet<long>> GetIssuersWithNonReferenceSamplesAsync()
    {
        var issuerIds = new HashSet<long>();

        using (var connection = new SqliteConnection(_connectionString))
        {
            await connection.OpenAsync();

            var command = connection.CreateCommand();
            command.CommandText = @"
                SELECT DISTINCT ct.issuer_id 
                FROM coin_types ct
                JOIN coin_type_samples cts ON ct.id = cts.coin_type_id
                WHERE cts.sample_type != 1 AND (cts.removed IS NULL OR cts.removed = 0)";

            using (var reader = await command.ExecuteReaderAsync())
            {
                while (await reader.ReadAsync())
                {
                    issuerIds.Add(reader.GetInt64(0));
                }
            }
        }

        return issuerIds;
    }
        public async Task UpdateCoinSampleImagesAsync(long coinTypeId, string oldObverseName, string newObverseName, string newReverseName)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            // Note: Numista schema for coin_type_samples might not have a primary key ID exposed easily to us?
            // User said: "coin_type_id = {coin_type_id} AND obverse_image = {old_obverse_image_name}"
            
            string query = @"
                UPDATE coin_type_samples 
                SET obverse_image = @newObv, reverse_image = @newRev 
                WHERE coin_type_id = @id AND obverse_image = @oldObv";

            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@newObv", newObverseName);
            command.Parameters.AddWithValue("@newRev", newReverseName);
            command.Parameters.AddWithValue("@id", coinTypeId);
            command.Parameters.AddWithValue("@oldObv", oldObverseName);

            await command.ExecuteNonQueryAsync();
        }

        public async Task DeleteCoinSampleAsync(long coinTypeId, string obverseImage)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            string query = "DELETE FROM coin_type_samples WHERE coin_type_id = @id AND obverse_image = @obv";
            
            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@id", coinTypeId);
            command.Parameters.AddWithValue("@obv", obverseImage);
            
            await command.ExecuteNonQueryAsync();
        }

        public async Task SoftDeleteCoinSampleAsync(long coinTypeId, string obverseImage)
        {
             using var connection = new SqliteConnection(_connectionString);
             await connection.OpenAsync();
             
             // Numista samples don't have PK, so update by coin_type_id AND obverse_image
             string query = "UPDATE coin_type_samples SET removed = 1 WHERE coin_type_id = @id AND obverse_image = @obv";
             
             using var command = connection.CreateCommand();
             command.CommandText = query;
             command.Parameters.AddWithValue("@id", coinTypeId);
             command.Parameters.AddWithValue("@obv", obverseImage);
             
             await command.ExecuteNonQueryAsync();
        }

        public async Task UpdateCoinSampleTypeAsync(long coinTypeId, string obverseImage, int newSampleType)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            string query = "UPDATE coin_type_samples SET sample_type = @newType WHERE coin_type_id = @id AND obverse_image = @obv";
            
            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@newType", newSampleType);
            command.Parameters.AddWithValue("@id", coinTypeId);
            command.Parameters.AddWithValue("@obv", obverseImage);
            
            await command.ExecuteNonQueryAsync();
        }

        public async Task TransferSampleToCoinTypeAsync(long sourceCoinTypeId, string obverseImage, long targetCoinTypeId)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            string query = "UPDATE coin_type_samples SET coin_type_id = @targetId, sample_type = 2 WHERE coin_type_id = @sourceId AND obverse_image = @obv";
            
            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@targetId", targetCoinTypeId);
            command.Parameters.AddWithValue("@sourceId", sourceCoinTypeId);
            command.Parameters.AddWithValue("@obv", obverseImage);
            
            await command.ExecuteNonQueryAsync();
        }

        public async Task UpdateSampleMarkingsAsync(long coinTypeId, string obverseImage, 
            bool isHolder, bool isCounterstamped, bool isRoll, bool containsHolder, bool containsText, bool isMultiCoin)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            string query = @"UPDATE coin_type_samples 
                           SET is_holder = @isHolder, 
                               is_counterstamped = @isCounterstamped, 
                               is_roll = @isRoll, 
                               contains_holder = @containsHolder, 
                               contains_text = @containsText, 
                               is_multi_coin = @isMultiCoin 
                           WHERE coin_type_id = @id AND obverse_image = @obv";
            
            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@isHolder", isHolder ? 1 : 0);
            command.Parameters.AddWithValue("@isCounterstamped", isCounterstamped ? 1 : 0);
            command.Parameters.AddWithValue("@isRoll", isRoll ? 1 : 0);
            command.Parameters.AddWithValue("@containsHolder", containsHolder ? 1 : 0);
            command.Parameters.AddWithValue("@containsText", containsText ? 1 : 0);
            command.Parameters.AddWithValue("@isMultiCoin", isMultiCoin ? 1 : 0);
            command.Parameters.AddWithValue("@id", coinTypeId);
            command.Parameters.AddWithValue("@obv", obverseImage);
            
            await command.ExecuteNonQueryAsync();
        }

        public async Task UpdateCoinFixedStatusAsync(long coinTypeId, bool isFixed)
        {
            using var connection = new SqliteConnection(_connectionString);
            await connection.OpenAsync();
            
            string query = "UPDATE coin_types SET fixed = @fixed WHERE id = @id";
            
            using var command = connection.CreateCommand();
            command.CommandText = query;
            command.Parameters.AddWithValue("@fixed", isFixed ? 1 : 0);
            command.Parameters.AddWithValue("@id", coinTypeId);
            
            await command.ExecuteNonQueryAsync();
        }

        public async Task<HashSet<long>> GetIssuerIdsWithCoinsAsync(bool onlyMultiSample, bool hideFixed, bool showOnlyFixed)
        {
             var issuerIds = new HashSet<long>();
             using (var connection = new SqliteConnection(_connectionString))
             {
                 await connection.OpenAsync();
                 var command = connection.CreateCommand();
                 
                 var sb = new System.Text.StringBuilder();
                 sb.Append("SELECT DISTINCT ct.issuer_id FROM coin_types ct JOIN coin_type_samples cts ON ct.id = cts.coin_type_id WHERE (cts.removed IS NULL OR cts.removed = 0) ");
                 
                 if (hideFixed)
                 {
                     sb.Append("AND (ct.fixed IS NULL OR ct.fixed = 0) ");
                 }
                 else if (showOnlyFixed)
                 {
                     sb.Append("AND (ct.fixed = 1) ");
                 }

                 sb.Append("GROUP BY ct.id HAVING 1=1 ");

                 if (onlyMultiSample)
                 {
                     sb.Append("AND COUNT(CASE WHEN cts.sample_type <> 1 THEN 1 END) > 0 ");
                 }

                 command.CommandText = sb.ToString();

                 using (var reader = await command.ExecuteReaderAsync())
                 {
                     while (await reader.ReadAsync())
                     {
                         issuerIds.Add(reader.GetInt64(0));
                     }
                 }
             }
             return issuerIds;
        }

        private bool _indexesChecked = false;

        private async Task EnsureIndexesAsync(SqliteConnection connection)
        {
            if (_indexesChecked) return;

            try 
            {
                var command = connection.CreateCommand();
                command.CommandText = @"
                    CREATE INDEX IF NOT EXISTS idx_irr_issuer_id ON issuers_rulers_rel(issuer_id);
                    CREATE INDEX IF NOT EXISTS idx_irr_ruler_id ON issuers_rulers_rel(ruler_id);
                    CREATE INDEX IF NOT EXISTS idx_irr_group_id ON issuers_rulers_rel(group_id);
                    CREATE INDEX IF NOT EXISTS idx_irr_issuer_ruler_id ON issuers_rulers_rel(issuer_id, ruler_id);
                    CREATE INDEX IF NOT EXISTS idx_irrg_id ON issuers_rulers_rel_groups(id);
                ";
                await command.ExecuteNonQueryAsync();
                _indexesChecked = true;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error creating indexes: {ex.Message}");
            }
        }

        public async Task<List<Ruler>> GetRulersForIssuerAsync(long issuerId)
        {
            var rulers = new List<Ruler>();
            
            // Keep legacy call path; currently a no-op for the current schema.
            await AutoAssociateRulersWithIssuerAsync(issuerId);

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                await EnsureIndexesAsync(connection);

                var command = connection.CreateCommand();
                command.CommandText = @"
                    SELECT
                        irr.rowid,
                        COALESCE(irr.ruler_id, irr.id) AS resolved_ruler_id,
                        COALESCE(NULLIF(TRIM(irr.name), ''), r.name, '') AS resolved_name,
                        COALESCE(g.name, '') AS group_name,
                        COALESCE(irr.group_id, 0) AS group_id,
                        irr.issuer_id
                    FROM issuers_rulers_rel AS irr
                    LEFT JOIN rulers AS r ON r.id = irr.ruler_id
                    LEFT JOIN issuers_rulers_rel_groups AS g ON g.id = irr.group_id
                    WHERE irr.issuer_id = @issuerId
                    ORDER BY
                        CASE WHEN irr.group_id IS NULL THEN 1 ELSE 0 END,
                        irr.group_id,
                        resolved_name";

                command.Parameters.AddWithValue("@issuerId", issuerId);

                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        rulers.Add(new Ruler
                        {
                            RowId = Convert.ToInt64(reader[0]),
                            Id = Convert.ToInt64(reader[1]),
                            Name = reader.IsDBNull(2) ? string.Empty : reader.GetString(2),
                            Period = reader.IsDBNull(3) ? string.Empty : reader.GetString(3),
                            YearsText = string.Empty,
                            PeriodOrder = reader.IsDBNull(4) ? 0 : Convert.ToInt32(reader[4]),
                            SubperiodOrder = null,
                            IssuerId = reader.IsDBNull(5) ? null : Convert.ToInt64(reader[5]),
                            IsManual = false
                        });
                    }
                }
            }
            
            return rulers;
        }

        public async Task AutoAssociateRulersWithIssuerAsync(long issuerId)
        {
            // The current DB schema stores direct issuer ownership in issuers_rulers_rel.issuer_id
            // and does not contain the legacy matching columns required for auto-association.
            await Task.CompletedTask;
        }

        public async Task ToggleRulerAssociationAsync(long rowId, long? issuerId)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = @"
                    UPDATE issuers_rulers_rel
                    SET issuer_id = @issuerId
                    WHERE rowid = @rowId";
                
                command.Parameters.AddWithValue("@issuerId", issuerId ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@rowId", rowId);
                
                await command.ExecuteNonQueryAsync();
            }
        }


        public async Task<List<Ruler>> GetRulersForIssuerFromNewTableAsync(long issuerId)
        {
            // Fallback for DBs that do not contain issuers_rulers_rel_new.
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                if (!await TableExistsAsync(connection, "issuers_rulers_rel_new"))
                {
                    return await GetRulersForIssuerAsync(issuerId);
                }
            }

            var rulers = new List<Ruler>();
            
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = @"
                    SELECT id, ruler_id, ruling_authority, period_years, extra, period, is_primary
                    FROM issuers_rulers_rel_new
                    WHERE issuer_id = @issuerId";
                
                command.Parameters.AddWithValue("@issuerId", issuerId);
                
                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        bool isPrimary = !reader.IsDBNull(6) && Convert.ToInt32(reader[6]) == 1;
                        
                        rulers.Add(new Ruler
                        {
                            RowId = reader.GetInt64(0), 
                            Id = reader.GetInt64(1),
                            Name = reader.IsDBNull(2) ? "" : reader.GetString(2),
                            YearsText = reader.IsDBNull(3) ? "" : reader.GetString(3),
                            Period = reader.IsDBNull(5) ? "" : reader.GetString(5),
                            IsPrimary = isPrimary
                        });
                    }
                }
            }
            
            return rulers
                .OrderBy(r => r.StartYear)
                .ThenByDescending(r => r.IsPrimary)
                .ThenBy(r => r.Name)
                .ToList();
        }

        public async Task<HashSet<long>> GetIssuerIdsWithRulersFromNewTableAsync()
        {
            var ids = new HashSet<long>();
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();

                var command = connection.CreateCommand();
                if (await TableExistsAsync(connection, "issuers_rulers_rel_new"))
                {
                    command.CommandText = "SELECT DISTINCT issuer_id FROM issuers_rulers_rel_new WHERE issuer_id IS NOT NULL";
                }
                else
                {
                    command.CommandText = "SELECT DISTINCT issuer_id FROM issuers_rulers_rel WHERE issuer_id IS NOT NULL";
                }
                
                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        ids.Add(reader.GetInt64(0));
                    }
                }
            }
            return ids;
        }

        public async Task TogglePeriodGroupAssociationAsync(long issuerId, string periodName, int periodOrder, bool associate)

        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                await EnsureIndexesAsync(connection);
                
                var command = connection.CreateCommand();
                
                if (associate)
                {
                    command.CommandText = @"
                        UPDATE issuers_rulers_rel
                        SET issuer_id = @issuerId
                        WHERE (group_id = @groupId OR (@groupId = 0 AND group_id IS NULL))
                          AND (issuer_id IS NULL OR issuer_id = @issuerId)";
                    command.Parameters.AddWithValue("@issuerId", issuerId);
                }
                else
                {
                    command.CommandText = @"
                        UPDATE issuers_rulers_rel
                        SET issuer_id = NULL
                        WHERE (group_id = @groupId OR (@groupId = 0 AND group_id IS NULL))
                          AND issuer_id = @issuerId";
                    command.Parameters.AddWithValue("@issuerId", issuerId);
                }
                
                command.Parameters.AddWithValue("@groupId", periodOrder);
                
                await command.ExecuteNonQueryAsync();
            }
        }

        public async Task<(string Name, string YearsText)?> GetRulerInfoAsync(long issuerId, int rulerId)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = @"
                    SELECT COALESCE(NULLIF(TRIM(irr.name), ''), r.name, '') AS resolved_name
                    FROM issuers_rulers_rel AS irr
                    LEFT JOIN rulers AS r ON r.id = irr.ruler_id
                    WHERE issuer_id = @issuerId AND ruler_id = @rulerId
                    LIMIT 1";
                
                command.Parameters.AddWithValue("@issuerId", issuerId);
                command.Parameters.AddWithValue("@rulerId", rulerId);

                using (var reader = await command.ExecuteReaderAsync())
                {
                    if (await reader.ReadAsync())
                    {
                        string name = reader.IsDBNull(0) ? "" : reader.GetString(0);
                        return (name, "");
                    }
                }
            }
            return null;
        }

        private static async Task<bool> TableExistsAsync(SqliteConnection connection, string tableName)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = @tableName LIMIT 1";
                command.Parameters.AddWithValue("@tableName", tableName);
                var result = await command.ExecuteScalarAsync();
                return result != null && result != DBNull.Value;
            }
        }

        public async Task<int?> GetShapeIdByNameAsync(string shapeName)
        {
            if (string.IsNullOrWhiteSpace(shapeName)) return null;

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = "SELECT id FROM shapes WHERE name = @name COLLATE NOCASE LIMIT 1";
                command.Parameters.AddWithValue("@name", shapeName.Trim());

                var result = await command.ExecuteScalarAsync();
                if (result != null && result != DBNull.Value)
                {
                    return Convert.ToInt32(result);
                }
            }
            return null;
        }

        public async Task<List<CoinShape>> GetShapesAsync()
        {
            var shapes = new List<CoinShape>();
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = "SELECT id, name, seq_number FROM shapes ORDER BY seq_number, name";
                
                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        shapes.Add(new CoinShape
                        {
                            Id = reader.GetInt32(0),
                            Name = reader.GetString(1),
                            SeqNumber = reader.IsDBNull(2) ? null : reader.GetInt32(2)
                        });
                    }
                }
            }
            return shapes;
        }

        public async Task<List<Period>> GetPeriodsForIssuerAsync(long issuerId)
        {
            var periods = new List<Period>();
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                var command = connection.CreateCommand();
                command.CommandText = @"
                    SELECT DISTINCT p.id, p.name 
                    FROM periods p 
                    JOIN coin_types ct ON p.id = ct.period_id 
                    WHERE ct.issuer_id = @issuerId
                    ORDER BY p.name";
                
                command.Parameters.AddWithValue("@issuerId", issuerId);

                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        periods.Add(new Period
                        {
                            Id = reader.GetInt32(0),
                            Name = reader.GetString(1)
                        });
                    }
                }
            }
            return periods;
        }

        public async Task<List<CalendarSystem>> GetCalendarSystemsAsync()
        {
            var systems = new List<CalendarSystem>();
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();

                var command = connection.CreateCommand();
                command.CommandText = "SELECT id, name FROM calendar_systems ORDER BY name"; 

                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        systems.Add(new CalendarSystem 
                        { 
                            Id = reader.GetInt32(0),
                            Name = reader.GetString(1)
                        });
                    }
                }
            }
            return systems;
        }
        
        public async Task<int> EnsureRulerRelationsForCoinTypeAsync(long coinTypeId, long issuerId, IEnumerable<RulerOption> selectedRulers)
        {
            var rulers = selectedRulers
                .Where(r => r != null && r.Id > 0 && !string.IsNullOrWhiteSpace(r.Name))
                .GroupBy(r => r.Id)
                .Select(g => g.First())
                .ToList();

            if (rulers.Count == 0)
            {
                return 0;
            }

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();

                using (var transaction = connection.BeginTransaction())
                {
                    int insertedCount = 0;
                    long seedId = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

                    try
                    {
                        for (int i = 0; i < rulers.Count; i++)
                        {
                            var ruler = rulers[i];

                            using (var existsIssuerRelCmd = connection.CreateCommand())
                            {
                                existsIssuerRelCmd.Transaction = transaction;
                                existsIssuerRelCmd.CommandText = @"
                                    SELECT 1
                                    FROM issuers_rulers_rel
                                    WHERE issuer_id = @issuerId AND ruler_id = @rulerId
                                    LIMIT 1";
                                existsIssuerRelCmd.Parameters.AddWithValue("@issuerId", issuerId);
                                existsIssuerRelCmd.Parameters.AddWithValue("@rulerId", ruler.Id);

                                var exists = await existsIssuerRelCmd.ExecuteScalarAsync();
                                if (exists == null)
                                {
                                    long newId = await GetNextIssuerRulerRelationIdAsync(connection, transaction, seedId + i);

                                    using (var insertIssuerRelCmd = connection.CreateCommand())
                                    {
                                        insertIssuerRelCmd.Transaction = transaction;
                                        insertIssuerRelCmd.CommandText = @"
                                            INSERT INTO issuers_rulers_rel (id, issuer_id, ruler_id, name)
                                            VALUES (@id, @issuerId, @rulerId, @name)";
                                        insertIssuerRelCmd.Parameters.AddWithValue("@id", newId);
                                        insertIssuerRelCmd.Parameters.AddWithValue("@issuerId", issuerId);
                                        insertIssuerRelCmd.Parameters.AddWithValue("@rulerId", ruler.Id);
                                        insertIssuerRelCmd.Parameters.AddWithValue("@name", ruler.Name.Trim());
                                        await insertIssuerRelCmd.ExecuteNonQueryAsync();
                                    }

                                    insertedCount++;
                                }
                            }

                            using (var existsCoinTypeRelCmd = connection.CreateCommand())
                            {
                                existsCoinTypeRelCmd.Transaction = transaction;
                                existsCoinTypeRelCmd.CommandText = @"
                                    SELECT 1
                                    FROM coin_types_rulers_rel
                                    WHERE coin_type_id = @coinTypeId AND ruler_id = @rulerId
                                    LIMIT 1";
                                existsCoinTypeRelCmd.Parameters.AddWithValue("@coinTypeId", coinTypeId);
                                existsCoinTypeRelCmd.Parameters.AddWithValue("@rulerId", ruler.Id);

                                var exists = await existsCoinTypeRelCmd.ExecuteScalarAsync();
                                if (exists == null)
                                {
                                    using (var insertCoinTypeRelCmd = connection.CreateCommand())
                                    {
                                        insertCoinTypeRelCmd.Transaction = transaction;
                                        insertCoinTypeRelCmd.CommandText = @"
                                            INSERT INTO coin_types_rulers_rel (coin_type_id, ruler_id)
                                            VALUES (@coinTypeId, @rulerId)";
                                        insertCoinTypeRelCmd.Parameters.AddWithValue("@coinTypeId", coinTypeId);
                                        insertCoinTypeRelCmd.Parameters.AddWithValue("@rulerId", ruler.Id);

                                        try
                                        {
                                            await insertCoinTypeRelCmd.ExecuteNonQueryAsync();
                                            insertedCount++;
                                        }
                                        catch (SqliteException ex) when (ex.Message.Contains("foreign key constraint failed", StringComparison.OrdinalIgnoreCase))
                                        {
                                            // Keep the dialog save flow resilient if a ruler is missing in rulers table.
                                        }
                                    }
                                }
                            }
                        }

                        transaction.Commit();
                        return insertedCount;
                    }
                    catch
                    {
                        transaction.Rollback();
                        throw;
                    }
                }
            }
        }

        private static async Task<long> GetNextIssuerRulerRelationIdAsync(SqliteConnection connection, SqliteTransaction transaction, long seed)
        {
            long candidateId = seed;

            while (true)
            {
                using (var command = connection.CreateCommand())
                {
                    command.Transaction = transaction;
                    command.CommandText = @"
                        SELECT 1
                        FROM issuers_rulers_rel
                        WHERE id = @id
                        LIMIT 1";
                    command.Parameters.AddWithValue("@id", candidateId);

                    var exists = await command.ExecuteScalarAsync();
                    if (exists == null)
                    {
                        return candidateId;
                    }
                }

                candidateId++;
            }
        }

        public async Task UpdateCoinAttributesAsync(long coinTypeId, int? shapeId, string? shapeInfo, 
            string? weightInfo, string? diameterInfo, string? thicknessInfo,
            decimal? weight, decimal? diameter, decimal? thickness, string? size,
            string? denominationText, decimal? valueAmount, string? denominationInfo1, decimal? valueAmountUsd, string? valueCurrencySymbol, string? denominationAlt,
            string? startDate, string? endDate, string? startNativeDate, string? endNativeDate, string? startMintDate, string? endMintDate,
            string? restrikeDate, string? restrikeStartMintDate, string? restrikeEndMintDate, string? erroneousDates, int? calendarSystemId, int? periodId,
            bool markAsFixed = false)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                using (var transaction = connection.BeginTransaction())
                {
                    try
                    {
                        string query = @"UPDATE coin_types 
                                       SET shape_id = @sid, shape_info = @info, 
                                           weight_info = @weightInfo, diameter_info = @diameterInfo, thickness_info = @thicknessInfo,
                                           weight = @weight, diameter = @diameter, thickness = @thickness,
                                           size = @size,
                                           denomination_text = @denText, value_amount = @denVal,
                                           denomination_info_1 = @denInfo1, value_amount_usd = @valUsd, value_currency_symbol = @valSym, denomination_alt = @denAlt,
                                           start_date = @startDate, end_date = @endDate, start_native_date = @startNativeDate, end_native_date = @endNativeDate, start_mint_date = @startMintDate, end_mint_date = @endMintDate,
                                           restrike_date = @restrikeDate, restrike_start_mint_date = @restrikeStartMintDate, restrike_end_mint_date = @restrikeEndMintDate,
                                           erroneous_dates = @errDates,
                                           calendar_system_id = @calSysId,
                                           period_id = @periodId
                                       WHERE id = @id";
                        
                        using (var command = connection.CreateCommand())
                        {
                            command.Transaction = transaction;
                            command.CommandText = query;
                            command.Parameters.AddWithValue("@sid", shapeId ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@info", shapeInfo ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@weightInfo", weightInfo ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@diameterInfo", diameterInfo ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@thicknessInfo", thicknessInfo ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@weight", weight ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@diameter", diameter ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@thickness", thickness ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@size", size ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@denText", denominationText ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@denVal", valueAmount ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@denInfo1", denominationInfo1 ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@valUsd", valueAmountUsd ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@valSym", valueCurrencySymbol ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@denAlt", denominationAlt ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@startDate", startDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@endDate", endDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@startNativeDate", startNativeDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@endNativeDate", endNativeDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@startMintDate", startMintDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@endMintDate", endMintDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@restrikeDate", restrikeDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@restrikeStartMintDate", restrikeStartMintDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@restrikeEndMintDate", restrikeEndMintDate ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@errDates", erroneousDates ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@calSysId", calendarSystemId ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@periodId", periodId ?? (object)DBNull.Value);
                            command.Parameters.AddWithValue("@id", coinTypeId);
                            
                            await command.ExecuteNonQueryAsync();
                        }

                        if (markAsFixed)
                        {
                            using (var fixedCmd = connection.CreateCommand())
                            {
                                fixedCmd.Transaction = transaction;
                                fixedCmd.CommandText = "UPDATE coin_types SET fixed = 1 WHERE id = @id";
                                fixedCmd.Parameters.AddWithValue("@id", coinTypeId);
                                await fixedCmd.ExecuteNonQueryAsync();
                            }
                        }

                        transaction.Commit();
                    }
                    catch
                    {
                        transaction.Rollback();
                        throw;
                    }
                }

                connection.Close();
            }
        }

    }
}
