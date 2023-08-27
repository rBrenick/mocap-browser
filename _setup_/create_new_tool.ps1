# This script takes the current tool directory
# clones it to another folder with the same parent directory
# renames all the instances of the current MocapFinder with the prompted new name
# searches through files and replaces in there as well

# parent directory of the mocap-finder
$TOOLS_DIR = (Get-Item -Path "..\").FullName

# define current tool name variables
$CURRENT_base_case = "mocap-finder"
$CURRENT_snake_case = "mocap_finder"
$CURRENT_PascalCase = "MocapFinder"
$CURRENT_TOOL_FOLDER = (Get-Item -Path ".").FullName

# get new tool name
$NEW_base_case = Read-Host -Prompt 'New Tool Name (in-this-format)'
$NEW_snake_case = $NEW_base_case.replace("-","_")
$NEW_PascalCase = (Get-Culture).TextInfo.ToTitleCase($NEW_base_case).replace("-", "")
$NEW_TOOL_FOLDER = $TOOLS_DIR + "\" + $NEW_base_case

echo ""

if (([string]::IsNullOrEmpty($NEW_base_case)))
{
    echo "No tool name was given. Exiting...`n "
    exit
}



# Clone to new folder
Copy-Item -Path $CURRENT_TOOL_FOLDER -Recurse -Destination $NEW_TOOL_FOLDER -Container


# Remove .git folder if it exists
$GIT_FOLDER = $NEW_TOOL_FOLDER + "\.git"
if(Test-Path -Path $GIT_FOLDER ){
    Get-ChildItem -Path $GIT_FOLDER -Recurse | Remove-Item -force -recurse
    Remove-Item $GIT_FOLDER -Force
}


# Rename files in folder
Get-ChildItem $NEW_TOOL_FOLDER -recurse | 
Foreach-Object {
    if ($_.Name -like '*' + $CURRENT_base_case + '*') {
        Rename-Item -Path $_.PSPath -NewName $_.Name.replace($CURRENT_base_case, $NEW_base_case)
    }
    if ($_.Name -like '*' + $CURRENT_snake_case + '*') {
        Rename-Item -Path $_.PSPath -NewName $_.Name.replace($CURRENT_snake_case, $NEW_snake_case)
    }
    
}

# Find instances of mocap_finder in files and replace them with the new tool name
Get-ChildItem $NEW_TOOL_FOLDER -recurse -File | 
Foreach-Object {
    
    $_.FullName
    
    ((Get-Content -path $_.FullName -Raw) -replace $CURRENT_base_case, $NEW_base_case) | Set-Content -Path $_.FullName
    ((Get-Content -path $_.FullName -Raw) -replace $CURRENT_snake_case, $NEW_snake_case) | Set-Content -Path $_.FullName
    ((Get-Content -path $_.FullName -Raw) -replace $CURRENT_PascalCase, $NEW_PascalCase) | Set-Content -Path $_.FullName
    ((Get-Content -path $_.FullName -Raw) -replace "mocap-finder", $NEW_base_case) | Set-Content -Path $_.FullName
    
}

echo ""
echo "New Tool: '$NEW_base_case' has been created at '$NEW_TOOL_FOLDER'"


# pause before exit
# cmd /c pause | out-null
# exit



