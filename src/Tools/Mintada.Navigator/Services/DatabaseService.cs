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
                             ct.denomination_text, ct.denomination_value, ct.denomination_info_1, ct.denomination_info_2, ct.denomination_alt
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
                                DenominationValue = !reader.IsDBNull(25) ? reader.GetDecimal(25) : null,
                                DenominationInfo1 = !reader.IsDBNull(26) ? reader.GetString(26) : null,
                                DenominationInfo2 = !reader.IsDBNull(27) ? reader.GetString(27) : null,
                                DenominationAlt = !reader.IsDBNull(28) ? reader.GetString(28) : null,
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
                    CREATE INDEX IF NOT EXISTS idx_irr_issuer_name ON issuers_rulers_rel(issuer_name);
                    CREATE INDEX IF NOT EXISTS idx_irr_period_order ON issuers_rulers_rel(period_order, subperiod_order);
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
            
            // 1. Ensure Auto-Association (linking) is performed first
            await AutoAssociateRulersWithIssuerAsync(issuerId);

            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                await EnsureIndexesAsync(connection);

                // 2. Fetch Logic matching AutoAssociate's criteria to find "Potential" rulers
                // We need to mirror the logic to know what "Generic" or "Specific" means here.
                string name = "";
                string territory = "";
                bool isSection = false;
                
                var issuerCmd = connection.CreateCommand();
                issuerCmd.CommandText = "SELECT numista_name, numista_territory_type, is_section FROM issuers WHERE id = @id";
                issuerCmd.Parameters.AddWithValue("@id", issuerId);
                
                using (var reader = await issuerCmd.ExecuteReaderAsync())
                {
                    if (await reader.ReadAsync())
                    {
                        name = reader.GetString(0);
                        territory = !reader.IsDBNull(1) ? reader.GetString(1) : "";
                        isSection = !reader.IsDBNull(2) && reader.GetBoolean(2);
                    }
                }

                bool abortAssociation = false;
                // A. Section vs Leaf Check
                if (isSection)
                {
                    var checkCmd = connection.CreateCommand();
                    checkCmd.CommandText = "SELECT count(*) FROM issuers WHERE numista_name = @name AND (is_section IS NULL OR is_section = 0)";
                    checkCmd.Parameters.AddWithValue("@name", name);
                    var count = Convert.ToInt32(await checkCmd.ExecuteScalarAsync());
                    if (count > 0) abortAssociation = true;
                }

                string sqlWhere = "1=0"; // Default to nothing if aborted
                if (!abortAssociation)
                {
                    // B. Ambiguity Check
                    bool hasTerritory = !string.IsNullOrEmpty(territory);
                    if (hasTerritory)
                    {
                        var checkAmbiguityCmd = connection.CreateCommand();
                        checkAmbiguityCmd.CommandText = "SELECT count(*) FROM issuers WHERE numista_name = @name AND (is_section IS NULL OR is_section = 0)";
                        checkAmbiguityCmd.Parameters.AddWithValue("@name", name);
                        var leafCount = Convert.ToInt32(await checkAmbiguityCmd.ExecuteScalarAsync());

                        if (leafCount > 1) sqlWhere = "issuer_name LIKE @combinedPattern";
                        else sqlWhere = "issuer_name = @simpleName OR issuer_name LIKE @combinedPattern";
                        
                        // Note: parameters added strictly to command later
                    }
                    else
                    {
                        sqlWhere = "issuer_name = @simpleName";
                    }
                }

                // 3. Fetch Rulers
                // We fetch:
                // a) Rulers explicitly assigned to us (issuer_id = @id)
                // b) Potential rulers: Match criteria AND are unassigned (issuer_id IS NULL)
                var command = connection.CreateCommand();
                command.CommandText = $@"
                    SELECT rowid, ruler_id, name, period, years_text, period_order, subperiod_order, issuer_id, is_manual
                    FROM issuers_rulers_rel
                    WHERE issuer_id = @issuerId
                       OR ( ({sqlWhere}) AND issuer_id IS NULL )
                    ORDER BY period_order, subperiod_order";
                
                command.Parameters.AddWithValue("@issuerId", issuerId);
                command.Parameters.AddWithValue("@simpleName", name);
                command.Parameters.AddWithValue("@combinedPattern", name + "%" + territory);
                
                using (var reader = await command.ExecuteReaderAsync())
                {
                    while (await reader.ReadAsync())
                    {
                        rulers.Add(ReadRuler(reader));
                    }
                }
            }
            
            return rulers;
        }


        private Ruler ReadRuler(SqliteDataReader reader)
        {
            return new Ruler
            {
                RowId = Convert.ToInt64(reader[0]),
                Id = Convert.ToInt64(reader[1]),
                Name = reader.GetString(2),
                Period = reader.IsDBNull(3) ? "" : reader.GetString(3),
                YearsText = reader.IsDBNull(4) ? "" : reader.GetString(4),
                PeriodOrder = reader.FieldCount > 5 && !reader.IsDBNull(5) ? Convert.ToInt32(reader[5]) : 0,
                SubperiodOrder = reader.FieldCount > 6 && !reader.IsDBNull(6) ? Convert.ToInt32(reader[6]) : null,
                IssuerId = reader.FieldCount > 7 && !reader.IsDBNull(7) ? Convert.ToInt64(reader[7]) : null,
                IsManual = reader.FieldCount > 8 && !reader.IsDBNull(8) && Convert.ToInt32(reader[8]) == 1
            };
        }

        public async Task AutoAssociateRulersWithIssuerAsync(long issuerId)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                await EnsureIndexesAsync(connection);

                // 1. Get Issuer Details First
                string name = "";
                string territory = "";
                bool isSection = false;
                
                var issuerCmd = connection.CreateCommand();
                issuerCmd.CommandText = "SELECT numista_name, numista_territory_type, is_section FROM issuers WHERE id = @id";
                issuerCmd.Parameters.AddWithValue("@id", issuerId);
                
                using (var reader = await issuerCmd.ExecuteReaderAsync())
                {
                    if (await reader.ReadAsync())
                    {
                        name = reader.GetString(0);
                        territory = !reader.IsDBNull(1) ? reader.GetString(1) : "";
                        isSection = !reader.IsDBNull(2) && reader.GetBoolean(2);
                    }
                    else return;
                }

                // Smart Association Logic:
                // If this is a Section (non-leaf), check if a Leaf node with the same name exists.
                // If a Leaf exists, it takes precedence, so we do NOT associate with this Section.
                if (isSection)
                {
                    var checkCmd = connection.CreateCommand();
                    checkCmd.CommandText = "SELECT count(*) FROM issuers WHERE numista_name = @name AND (is_section IS NULL OR is_section = 0)";
                    checkCmd.Parameters.AddWithValue("@name", name);
                    var count = Convert.ToInt32(await checkCmd.ExecuteScalarAsync());
                    
                    if (count > 0)
                    {
                        // A leaf node exists, so we skip association for this section.
                        return; 
                    }
                }

                var command = connection.CreateCommand();
                
                // 2. Perform Update with optimized WHERE clause
                // Only update non-manual rows
                bool hasTerritory = !string.IsNullOrEmpty(territory);
                string sqlWhere;
                
                if (hasTerritory)
                {
                    // Check if *ANY* other Leaf issuer (non-section) exists with the same name.
                    // If multiple Leaf nodes share this name (Count > 1), it is ambiguous which one the "Simple Name" rulers belong to.
                    // In that case, we should be conservative and ONLY claim rulers that match our specific combined pattern (Name + Territory).
                    // We do not want to randomly assign generic/simple rulers to one of the siblings.
                    var checkAmbiguityCmd = connection.CreateCommand();
                    checkAmbiguityCmd.CommandText = "SELECT count(*) FROM issuers WHERE numista_name = @name AND (is_section IS NULL OR is_section = 0)";
                    checkAmbiguityCmd.Parameters.AddWithValue("@name", name);
                    var leafCount = Convert.ToInt32(await checkAmbiguityCmd.ExecuteScalarAsync());

                    if (leafCount > 1)
                    {
                         // Ambiguity exists (e.g. "CityA (Type1)" and "CityA (Type2)" both exist).
                         // Or "Austria (Generic)" and "Austria (Empire)" both exist.
                         // We only claim the strictly matching rulers.
                         sqlWhere = "issuer_name LIKE @combinedPattern";
                    }
                    else
                    {
                         // We are the ONLY Leaf node with this name.
                         // Safe to claim generic/simple matches too.
                         sqlWhere = "issuer_name = @simpleName OR issuer_name LIKE @combinedPattern";
                    }
                    command.Parameters.AddWithValue("@combinedPattern", name + "%" + territory);
                }
                else
                {
                    sqlWhere = "issuer_name = @simpleName";
                }
                
                command.Parameters.AddWithValue("@simpleName", name);
                command.Parameters.AddWithValue("@issuerId", issuerId);

                command.CommandText = $@"
                    UPDATE issuers_rulers_rel
                    SET issuer_id = @issuerId
                    WHERE (issuer_id IS NULL OR issuer_id = @issuerId)
                      AND (is_manual IS NULL OR is_manual = 0)
                      AND ({sqlWhere})";
                
                await command.ExecuteNonQueryAsync();

                // 3. Dissociate invalid auto-associations
                // If any rulers are currently associated with this issuer (non-manually)
                // but DO NOT match the current strict criteria (e.g. they matched the old relaxed criteria),
                // we must release them (set issuer_id = NULL).
                // This self-corrects cases like 'Qandahar' vs 'Qandahar, City Of' where mixed associations persist.
                var cleanupCmd = connection.CreateCommand();
                cleanupCmd.Parameters.AddWithValue("@combinedPattern", name + "%" + territory);
                cleanupCmd.Parameters.AddWithValue("@simpleName", name);
                cleanupCmd.Parameters.AddWithValue("@issuerId", issuerId);
                
                cleanupCmd.CommandText = $@"
                    UPDATE issuers_rulers_rel
                    SET issuer_id = NULL
                    WHERE issuer_id = @issuerId
                      AND (is_manual IS NULL OR is_manual = 0)
                      AND NOT ({sqlWhere})";

                await cleanupCmd.ExecuteNonQueryAsync();
            }
        }

        public async Task ToggleRulerAssociationAsync(long rowId, long? issuerId)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                var command = connection.CreateCommand();
                command.CommandText = @"
                    UPDATE issuers_rulers_rel
                    SET issuer_id = @issuerId, is_manual = 1
                    WHERE rowid = @rowId";
                
                command.Parameters.AddWithValue("@issuerId", issuerId ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@rowId", rowId);
                
                await command.ExecuteNonQueryAsync();
            }
        }


        public async Task<List<Ruler>> GetRulersForIssuerFromNewTableAsync(long issuerId)
        {
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
                        bool isPrimary = !reader.IsDBNull(6) && (reader.GetBoolean(6) || reader.GetInt32(6) == 1);
                        
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
                command.CommandText = "SELECT DISTINCT issuer_id FROM issuers_rulers_rel_new WHERE issuer_id IS NOT NULL";
                
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
                    // Associate all rulers in this period with this issuer
                    // But we MUST check period/periodOrder match
                    command.CommandText = @"
                        UPDATE issuers_rulers_rel
                        SET issuer_id = @issuerId, is_manual = 1
                        WHERE period = @period AND period_order = @periodOrder";
                    command.Parameters.AddWithValue("@issuerId", issuerId);
                }
                else
                {
                    // Disassociate (set issuer_id to NULL) only for rulers currently associated with this issuer
                    command.CommandText = @"
                        UPDATE issuers_rulers_rel
                        SET issuer_id = NULL, is_manual = 1
                        WHERE period = @period AND period_order = @periodOrder AND issuer_id = @issuerId";
                    command.Parameters.AddWithValue("@issuerId", issuerId);
                }
                
                command.Parameters.AddWithValue("@period", periodName);
                command.Parameters.AddWithValue("@periodOrder", periodOrder);
                
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
                    SELECT name, years_text 
                    FROM issuers_rulers_rel 
                    WHERE issuer_id = @issuerId AND ruler_id = @rulerId
                    LIMIT 1";
                
                command.Parameters.AddWithValue("@issuerId", issuerId);
                command.Parameters.AddWithValue("@rulerId", rulerId);

                using (var reader = await command.ExecuteReaderAsync())
                {
                    if (await reader.ReadAsync())
                    {
                        string name = reader.GetString(0);
                        string years = reader.IsDBNull(1) ? "" : reader.GetString(1);
                        return (name, years);
                    }
                }
            }
            return null;
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

        public async Task UpdateCoinAttributesAsync(long coinTypeId, int? shapeId, string? shapeInfo, 
            string? weightInfo, string? diameterInfo, string? thicknessInfo,
            decimal? weight, decimal? diameter, decimal? thickness, string? size,
            string? denominationText, decimal? denominationValue, string? denominationInfo1, string? denominationInfo2, string? denominationAlt)
        {
            using (var connection = new SqliteConnection(_connectionString))
            {
                await connection.OpenAsync();
                
                string query = @"UPDATE coin_types 
                               SET shape_id = @sid, shape_info = @info, 
                                   weight_info = @weightInfo, diameter_info = @diameterInfo, thickness_info = @thicknessInfo,
                                   weight = @weight, diameter = @diameter, thickness = @thickness,
                                   size = @size,
                                   denomination_text = @denText, denomination_value = @denVal,
                                   denomination_info_1 = @denInfo1, denomination_info_2 = @denInfo2, denomination_alt = @denAlt
                               WHERE id = @id";
                
                using var command = connection.CreateCommand();
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
                command.Parameters.AddWithValue("@denVal", denominationValue ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@denInfo1", denominationInfo1 ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@denInfo2", denominationInfo2 ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@denAlt", denominationAlt ?? (object)DBNull.Value);
                command.Parameters.AddWithValue("@id", coinTypeId);
                
                await command.ExecuteNonQueryAsync();
            }
        }

    }
}
