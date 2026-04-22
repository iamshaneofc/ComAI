$base = "C:\AIEcommerce\ComAI"
$dirs = @(
    "app\api\v1\webhooks",
    "app\modules\auth",
    "app\modules\store",
    "app\modules\product",
    "app\modules\order",
    "app\modules\customer",
    "app\modules\conversation",
    "app\modules\memory",
    "app\adapters\shopify",
    "app\adapters\custom_website",
    "app\adapters\whatsapp",
    "app\adapters\voice",
    "app\ai\intent",
    "app\ai\retrieval",
    "app\ai\ranking",
    "app\ai\prompt\templates",
    "app\ai\memory",
    "app\ai\providers",
    "app\services",
    "app\repositories",
    "app\models",
    "app\schemas",
    "app\events\handlers",
    "app\channels",
    "app\workers\tasks",
    "app\utils",
    "app\core",
    "migrations\versions",
    "tests\unit",
    "tests\integration",
    "tests\fixtures",
    "scripts",
    "docker"
)
foreach ($d in $dirs) {
    $p = Join-Path $base $d
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    $i = Join-Path $p "__init__.py"
    if (-not (Test-Path $i)) { "" | Set-Content -Path $i -NoNewline }
}
Write-Host "All directories and __init__.py stubs created successfully."
