$envContent = Get-Content config/printify.local.env -Raw
$key = ($envContent | Select-String 'PRINTIFY_API_KEY=([^\r\n]+)').Matches.Groups[1].Value.Trim()
$shop = ($envContent | Select-String 'PRINTIFY_SHOP_ID=(\d+)').Matches.Groups[1].Value
$all = @()
$page = 1
do {
  $url = "https://api.printify.com/v1/shops/$shop/products.json?page=$page&limit=50"
  $resp = Invoke-RestMethod -Uri $url -Headers @{Authorization="Bearer $key"} -Method Get
  if ($resp.data) { $all += $resp.data }
  $page++
} while ($resp.next_page_url -and $page -lt 20)

$byTitle = @{}
$all | ForEach-Object {
  $t = $_.title
  if (-not $byTitle.ContainsKey($t)) { $byTitle[$t] = @() }
  $byTitle[$t] += $_
}

$toDelete = @()
$dups = $byTitle.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 }
$dups | ForEach-Object {
  $items = $_.Value
  # Keep the first, delete the rest
  $keep = $items[0]
  $extras = $items | Select-Object -Skip 1
  $toDelete += $extras | ForEach-Object { $_.id }
}

Write-Host "Found $($dups.Count) duplicate groups."
Write-Host "Will delete $($toDelete.Count) extra products (keeping 1 per group)."

$deleted = 0
$toDelete | ForEach-Object {
  $id = $_
  try {
    Invoke-RestMethod -Uri "https://api.printify.com/v1/shops/$shop/products/$id.json" -Headers @{Authorization="Bearer $key"} -Method Delete -ErrorAction Stop | Out-Null
    $deleted++
    if ($deleted % 10 -eq 0) { Write-Host "Deleted $deleted so far..." }
  } catch {
    Write-Host "Failed to delete $id : $($_.Exception.Message)"
  }
}
Write-Host "Cleanup done. Deleted $deleted products."
