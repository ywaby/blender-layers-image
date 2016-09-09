

z7 = "\"D:/Program Files/7-Zip/7z.exe\""
function package()
    os.execute(z7.." a layers_image.zip ./src/*")
    os.execute(z7.." d layers_image.zip */__pycache__/")
end

task = arg[1]
if task == "package" then
    package()
end