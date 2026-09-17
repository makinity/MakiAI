$word = New-Object -ComObject Word.Application
$word.Visible = $false
$inPath = "C:\Knowledge-Base\docs\Weekly_Time_Management_Plan_UPDATED.docx"
$outPath = "C:\Knowledge-Base\docs\Weekly_Time_Management_Plan_UPDATED.pdf"

Write-Output "Opening $inPath..."
$doc = $word.Documents.Open($inPath)
$wdFormatPDF = 17
$doc.SaveAs([ref]$outPath, [ref]$wdFormatPDF)
$doc.Close([ref]$false)
$word.Quit()
Write-Output "PDF conversion complete: $outPath"
