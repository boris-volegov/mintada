using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Mintada.Data.Migrations
{
    /// <inheritdoc />
    public partial class CascadeIssuerDependents : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_issuers_issue_types_rel_issuers_IssuerId",
                table: "issuers_issue_types_rel");

            migrationBuilder.DropForeignKey(
                name: "FK_issuers_rulers_rel_issuers_IssuerId",
                table: "issuers_rulers_rel");

            migrationBuilder.DropForeignKey(
                name: "FK_issuers_rulers_rel_groups_issuers_IssuerId",
                table: "issuers_rulers_rel_groups");

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_issue_types_rel_issuers_IssuerId",
                table: "issuers_issue_types_rel",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_rulers_rel_issuers_IssuerId",
                table: "issuers_rulers_rel",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_rulers_rel_groups_issuers_IssuerId",
                table: "issuers_rulers_rel_groups",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_issuers_issue_types_rel_issuers_IssuerId",
                table: "issuers_issue_types_rel");

            migrationBuilder.DropForeignKey(
                name: "FK_issuers_rulers_rel_issuers_IssuerId",
                table: "issuers_rulers_rel");

            migrationBuilder.DropForeignKey(
                name: "FK_issuers_rulers_rel_groups_issuers_IssuerId",
                table: "issuers_rulers_rel_groups");

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_issue_types_rel_issuers_IssuerId",
                table: "issuers_issue_types_rel",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_rulers_rel_issuers_IssuerId",
                table: "issuers_rulers_rel",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);

            migrationBuilder.AddForeignKey(
                name: "FK_issuers_rulers_rel_groups_issuers_IssuerId",
                table: "issuers_rulers_rel_groups",
                column: "IssuerId",
                principalTable: "issuers",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);
        }
    }
}
