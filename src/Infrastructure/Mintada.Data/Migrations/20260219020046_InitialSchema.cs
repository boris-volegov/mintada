using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace Mintada.Data.Migrations
{
    /// <inheritdoc />
    public partial class InitialSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "calendar_systems",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_calendar_systems", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "issue_types",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issue_types", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "issuer_types",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuer_types", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "rulers",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false),
                    PortraitUrl = table.Column<string>(type: "text", nullable: true),
                    Info = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_rulers", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "shapes",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    Name = table.Column<string>(type: "text", nullable: false),
                    SeqNumber = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_shapes", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "issuers",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    ParentId = table.Column<int>(type: "integer", nullable: true),
                    IssuerTypeId = table.Column<int>(type: "integer", nullable: true),
                    Name = table.Column<string>(type: "text", nullable: true),
                    UrlSlug = table.Column<string>(type: "text", nullable: true),
                    TerritoryType = table.Column<string>(type: "text", nullable: true),
                    IsHistoricalPeriod = table.Column<bool>(type: "boolean", nullable: false),
                    IsSection = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuers", x => x.Id);
                    table.ForeignKey(
                        name: "FK_issuers_issuer_types_IssuerTypeId",
                        column: x => x.IssuerTypeId,
                        principalTable: "issuer_types",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_issuers_issuers_ParentId",
                        column: x => x.ParentId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "coinage_periods",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    Name = table.Column<string>(type: "text", nullable: false),
                    UnitRelationText = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_coinage_periods", x => x.Id);
                    table.ForeignKey(
                        name: "FK_coinage_periods_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "issuer_alt_names",
                columns: table => new
                {
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    AltName = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuer_alt_names", x => new { x.IssuerId, x.AltName });
                    table.ForeignKey(
                        name: "FK_issuer_alt_names_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "issuers_issue_types_rel",
                columns: table => new
                {
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    IssueTypeId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuers_issue_types_rel", x => new { x.IssuerId, x.IssueTypeId });
                    table.ForeignKey(
                        name: "FK_issuers_issue_types_rel_issue_types_IssueTypeId",
                        column: x => x.IssueTypeId,
                        principalTable: "issue_types",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_issuers_issue_types_rel_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "issuers_rulers_rel_groups",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    Name = table.Column<string>(type: "text", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuers_rulers_rel_groups", x => x.Id);
                    table.UniqueConstraint("AK_issuers_rulers_rel_groups_Id_IssuerId", x => new { x.Id, x.IssuerId });
                    table.ForeignKey(
                        name: "FK_issuers_rulers_rel_groups_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "coin_types",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    Title = table.Column<string>(type: "text", nullable: false),
                    Subtitle = table.Column<string>(type: "text", nullable: true),
                    EdgeImage = table.Column<string>(type: "text", nullable: true),
                    ShapeId = table.Column<int>(type: "integer", nullable: true),
                    CoinagePeriodId = table.Column<int>(type: "integer", nullable: true),
                    RarityIndex = table.Column<int>(type: "integer", nullable: true),
                    UrlSlug = table.Column<string>(type: "text", nullable: false),
                    DateTimeInserted = table.Column<DateTime>(type: "timestamp with time zone", nullable: false),
                    IssueTypeId = table.Column<int>(type: "integer", nullable: false),
                    CalendarSystemId = table.Column<int>(type: "integer", nullable: true),
                    Weight = table.Column<decimal>(type: "numeric", nullable: true),
                    Diameter = table.Column<decimal>(type: "numeric", nullable: true),
                    Thickness = table.Column<decimal>(type: "numeric", nullable: true),
                    Size = table.Column<string>(type: "text", nullable: true),
                    DenominationText = table.Column<string>(type: "text", nullable: true),
                    DenominationUnit = table.Column<string>(type: "text", nullable: true),
                    StartDate = table.Column<int>(type: "integer", nullable: true),
                    EndDate = table.Column<int>(type: "integer", nullable: true),
                    StartNativeDate = table.Column<int>(type: "integer", nullable: true),
                    EndNativeDate = table.Column<int>(type: "integer", nullable: true),
                    StartMintDate = table.Column<int>(type: "integer", nullable: true),
                    EndMintDate = table.Column<int>(type: "integer", nullable: true),
                    RestrikeStartMintDate = table.Column<int>(type: "integer", nullable: true),
                    RestrikeEndMintDate = table.Column<int>(type: "integer", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_coin_types", x => x.Id);
                    table.ForeignKey(
                        name: "FK_coin_types_calendar_systems_CalendarSystemId",
                        column: x => x.CalendarSystemId,
                        principalTable: "calendar_systems",
                        principalColumn: "Id");
                    table.ForeignKey(
                        name: "FK_coin_types_coinage_periods_CoinagePeriodId",
                        column: x => x.CoinagePeriodId,
                        principalTable: "coinage_periods",
                        principalColumn: "Id");
                    table.ForeignKey(
                        name: "FK_coin_types_issue_types_IssueTypeId",
                        column: x => x.IssueTypeId,
                        principalTable: "issue_types",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_coin_types_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_coin_types_issuers_issue_types_rel_IssuerId_IssueTypeId",
                        columns: x => new { x.IssuerId, x.IssueTypeId },
                        principalTable: "issuers_issue_types_rel",
                        principalColumns: new[] { "IssuerId", "IssueTypeId" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_coin_types_shapes_ShapeId",
                        column: x => x.ShapeId,
                        principalTable: "shapes",
                        principalColumn: "Id");
                });

            migrationBuilder.CreateTable(
                name: "issuers_rulers_rel",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    IssuerId = table.Column<int>(type: "integer", nullable: false),
                    GroupId = table.Column<int>(type: "integer", nullable: true),
                    RulerId = table.Column<int>(type: "integer", nullable: false),
                    Name = table.Column<string>(type: "text", nullable: true),
                    RuleType = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_issuers_rulers_rel", x => x.Id);
                    table.ForeignKey(
                        name: "FK_issuers_rulers_rel_issuers_IssuerId",
                        column: x => x.IssuerId,
                        principalTable: "issuers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_issuers_rulers_rel_issuers_rulers_rel_groups_GroupId_Issuer~",
                        columns: x => new { x.GroupId, x.IssuerId },
                        principalTable: "issuers_rulers_rel_groups",
                        principalColumns: new[] { "Id", "IssuerId" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_issuers_rulers_rel_rulers_RulerId",
                        column: x => x.RulerId,
                        principalTable: "rulers",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "coin_type_samples",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    CoinTypeId = table.Column<int>(type: "integer", nullable: false),
                    ObverseImage = table.Column<string>(type: "text", nullable: true),
                    ReverseImage = table.Column<string>(type: "text", nullable: true),
                    SampleType = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_coin_type_samples", x => x.Id);
                    table.ForeignKey(
                        name: "FK_coin_type_samples_coin_types_CoinTypeId",
                        column: x => x.CoinTypeId,
                        principalTable: "coin_types",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "coin_types_issuers_rulers_rel",
                columns: table => new
                {
                    CoinTypeId = table.Column<int>(type: "integer", nullable: false),
                    IssuerRulerRelId = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_coin_types_issuers_rulers_rel", x => new { x.CoinTypeId, x.IssuerRulerRelId });
                    table.ForeignKey(
                        name: "FK_coin_types_issuers_rulers_rel_coin_types_CoinTypeId",
                        column: x => x.CoinTypeId,
                        principalTable: "coin_types",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_coin_types_issuers_rulers_rel_issuers_rulers_rel_IssuerRule~",
                        column: x => x.IssuerRulerRelId,
                        principalTable: "issuers_rulers_rel",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_coin_type_samples_CoinTypeId",
                table: "coin_type_samples",
                column: "CoinTypeId");

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_CalendarSystemId",
                table: "coin_types",
                column: "CalendarSystemId");

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_CoinagePeriodId",
                table: "coin_types",
                column: "CoinagePeriodId");

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_IssuerId_IssueTypeId",
                table: "coin_types",
                columns: new[] { "IssuerId", "IssueTypeId" });

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_IssueTypeId",
                table: "coin_types",
                column: "IssueTypeId");

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_ShapeId",
                table: "coin_types",
                column: "ShapeId");

            migrationBuilder.CreateIndex(
                name: "IX_coin_types_issuers_rulers_rel_IssuerRulerRelId",
                table: "coin_types_issuers_rulers_rel",
                column: "IssuerRulerRelId");

            migrationBuilder.CreateIndex(
                name: "IX_coinage_periods_IssuerId",
                table: "coinage_periods",
                column: "IssuerId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_IssuerTypeId",
                table: "issuers",
                column: "IssuerTypeId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_ParentId",
                table: "issuers",
                column: "ParentId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_issue_types_rel_IssueTypeId",
                table: "issuers_issue_types_rel",
                column: "IssueTypeId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_rulers_rel_GroupId_IssuerId",
                table: "issuers_rulers_rel",
                columns: new[] { "GroupId", "IssuerId" });

            migrationBuilder.CreateIndex(
                name: "IX_issuers_rulers_rel_IssuerId",
                table: "issuers_rulers_rel",
                column: "IssuerId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_rulers_rel_RulerId",
                table: "issuers_rulers_rel",
                column: "RulerId");

            migrationBuilder.CreateIndex(
                name: "IX_issuers_rulers_rel_groups_IssuerId",
                table: "issuers_rulers_rel_groups",
                column: "IssuerId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "coin_type_samples");

            migrationBuilder.DropTable(
                name: "coin_types_issuers_rulers_rel");

            migrationBuilder.DropTable(
                name: "issuer_alt_names");

            migrationBuilder.DropTable(
                name: "coin_types");

            migrationBuilder.DropTable(
                name: "issuers_rulers_rel");

            migrationBuilder.DropTable(
                name: "calendar_systems");

            migrationBuilder.DropTable(
                name: "coinage_periods");

            migrationBuilder.DropTable(
                name: "issuers_issue_types_rel");

            migrationBuilder.DropTable(
                name: "shapes");

            migrationBuilder.DropTable(
                name: "issuers_rulers_rel_groups");

            migrationBuilder.DropTable(
                name: "rulers");

            migrationBuilder.DropTable(
                name: "issue_types");

            migrationBuilder.DropTable(
                name: "issuers");

            migrationBuilder.DropTable(
                name: "issuer_types");
        }
    }
}
