for file in ../../data/xml/*.xml
do
  echo $file
  python3 protect.py "$file" "$file"
done