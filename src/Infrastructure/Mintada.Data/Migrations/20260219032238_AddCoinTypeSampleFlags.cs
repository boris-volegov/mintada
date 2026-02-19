using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mintada.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddCoinTypeSampleFlags : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<bool>(
                name: "ContainsHolder",
                table: "coin_type_samples",
                type: "boolean",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsCounterstamped",
                table: "coin_type_samples",
                type: "boolean",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsHolder",
                table: "coin_type_samples",
                type: "boolean",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsMultiCoin",
                table: "coin_type_samples",
                type: "boolean",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsRoll",
                table: "coin_type_samples",
                type: "boolean",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ContainsHolder",
                table: "coin_type_samples");

            migrationBuilder.DropColumn(
                name: "IsCounterstamped",
                table: "coin_type_samples");

            migrationBuilder.DropColumn(
                name: "IsHolder",
                table: "coin_type_samples");

            migrationBuilder.DropColumn(
                name: "IsMultiCoin",
                table: "coin_type_samples");

            migrationBuilder.DropColumn(
                name: "IsRoll",
                table: "coin_type_samples");
        }
    }
}
