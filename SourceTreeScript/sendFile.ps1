$Outlook = New-Object -ComObject Outlook.Application
$Mail = $Outlook.CreateItem(0)
#$Mail.To = "v-welian@microsoft.com;v-johch@microsoft.com;v-junlch@microsoft.com;v-yiso@microsoft.com;v-dazen@microsoft.com"
$Mail.To = "v-dazen@microsoft.com"
$Today = Get-Date -Format "yyyy-MM-dd"
$Mail.Subject = "ACN Broken Link - " + $Today
$Mail.Body ="Hi guys,`r`n`r`nAttached is the ACN broken link.`r`n`r`nBest Regards,`r`nJack Zeng"

$file = "E:\GitHub\SourceTreeScript\SourceTreeScript\output.zip "
$Mail.Attachments.Add($file)
$Mail.Send()