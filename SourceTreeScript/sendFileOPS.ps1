$Outlook = New-Object -ComObject Outlook.Application
$Mail = $Outlook.CreateItem(0)
$Mail.To = "v-johch@microsoft.com;v-junlch@microsoft.com;v-yiso@microsoft.com;v-dazen@microsoft.com;v-yeche@microsoft.com"
#$Mail.To = "v-dazen@microsoft.com"
$Today = Get-Date -Format "yyyy-MM-dd"
$Mail.Subject = "mc-docs-pr.zh-cn Broken Link - " + $Today
$Mail.Body ="Hi guys,`r`n`r`nAttached is the mc-docs-pr.zh-cn broken link.`r`n`r`nBest Regards,`r`nJack Zeng"

$file1 = "E:\GitHub\SourceTreeScript\SourceTreeScript\links_output.zip"
$file2 = "E:\GitHub\SourceTreeScript\SourceTreeScript\anchors_output.zip"
$Mail.Attachments.Add($file1)
$Mail.Attachments.Add($file2)
$Mail.Send()