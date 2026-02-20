using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mintada.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddIssuerRulerRelYearColumns : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "EndYear",
                table: "issuers_rulers_rel",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsApprox",
                table: "issuers_rulers_rel",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<int>(
                name: "StartYear",
                table: "issuers_rulers_rel",
                type: "integer",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "EndYear",
                table: "issuers_rulers_rel");

            migrationBuilder.DropColumn(
                name: "IsApprox",
                table: "issuers_rulers_rel");

            migrationBuilder.DropColumn(
                name: "StartYear",
                table: "issuers_rulers_rel");
        }
    }
}
