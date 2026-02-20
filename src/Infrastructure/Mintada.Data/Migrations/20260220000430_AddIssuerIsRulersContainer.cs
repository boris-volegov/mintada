using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mintada.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddIssuerIsRulersContainer : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "IsRulersContainer",
                table: "issuers",
                type: "boolean",
                nullable: false,
                defaultValue: false);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "IsRulersContainer",
                table: "issuers");
        }
    }
}
