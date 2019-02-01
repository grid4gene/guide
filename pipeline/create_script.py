
num_split=5

bqsr_str1 = "java -jar /home/test/WGS_pipeline/TOOLS/bin/GenomeAnalysisTK.jar  -nct 3 -T BaseRecalibrator -l INFO  -R /home/test/WGS_pipeline/reference/hg19.fasta   -knownSites /home/test/WGS_pipeline/reference/Mills_and_1000G_gold_standard.indels.hg19.sites.vcf -knownSites /home/test/WGS_pipeline/reference/1000G_phase1.indels.hg19.sites.vcf  -I  /home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned.bam -o "
bqsr_str2 = "/home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned."
bqsr_str3 = ".grp "

merge_bqsr="java -cp /home/test/WGS_pipeline/TOOLS/bin/GenomeAnalysisTK.jar org.broadinstitute.gatk.tools.GatherBqsrReports O=/home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned.grp "

apply_str1="java -jar /home/test/WGS_pipeline/TOOLS/bin/GenomeAnalysisTK.jar -nct 3 -T PrintReads -R /home/test/WGS_pipeline/reference/hg19.fasta -I /home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned.bam -BQSR /home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned.grp -o "
apply_str2="/home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned-recal." 
apply_str3=".bam " 

merge_bam="java -jar /home/test/WGS_pipeline/TOOLS/bin/picard.jar GatherBamFiles CREATE_INDEX=true CREATE_MD5_FILE=true OUTPUT=/home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned-recal.bam "
merge_bam_str1="/home/test/new_test_data/6150_base/pipe4-3.8-ali-sorted-RG-rmdup-realigned-recal."
merge_bam_str2=".bam"



with open("/home/test/WGS_pipeline/reference/hg19.dict", "r") as ref_dict_file:
    sequence_tuple_list = []
    longest_sequence = 0
    for line in ref_dict_file:
        if line.startswith("@SQ"):
            line_split = line.split("\t")
            # (Sequence_Name, Sequence_Length)
            sequence_tuple_list.append((line_split[1].split("SN:")[1], int(line_split[2].split("LN:")[1])))
    #longest_sequence = sorted(sequence_tuple_list, key=lambda x: x[1], reverse=True)[0][1]
    seq_len = [line[1] for line in sequence_tuple_list]
    split_len = sum(seq_len)/num_split
    
    #total_sequence = sum(sequence_tuple_list[:][])
# We are adding this to the intervals because hg38 has contigs named with embedded colons (:) and a bug in
# some versions of GATK strips off the last element after a colon, so we add this as a sacrificial element.
#hg38_protection_tag = ":1+"
# initialize the tsv string with the first sequence
#tsv_string = sequence_tuple_list[0][0] + hg38_protection_tag
tsv_string = "-L " + sequence_tuple_list[0][0]
temp_size = sequence_tuple_list[0][1]
for sequence_tuple in sequence_tuple_list[1:]:
    #if temp_size + sequence_tuple[1] <= longest_sequence:
    if temp_size + sequence_tuple[1] <= split_len:
        temp_size += sequence_tuple[1]
        #tsv_string += "\t" + sequence_tuple[0] + hg38_protection_tag
        tsv_string += " -L " + sequence_tuple[0]
    else:
        #tsv_string += "\n" + sequence_tuple[0] + hg38_protection_tag
        tsv_string += "\n-L " + sequence_tuple[0]
        temp_size = sequence_tuple[1]
#tsv_string += "\n"

#create the bqsr.sh
count = 0
cli=""
bqsr_list = tsv_string.splitlines()
lenght = len(bqsr_list)
while count < lenght :
    cli += bqsr_str1 + bqsr_str2 + str(count) + bqsr_str3 + bqsr_list[count] + "\n"
    count += 1

with open("bqsr.sh", "w") as bqsr_file:
  bqsr_file.write(cli)
  bqsr_file.close()

count=0
cli=merge_bqsr
lenght = len(bqsr_list)
while count < lenght :
    cli += "I=" + bqsr_str2 + str(count) + bqsr_str3 + " "
    count += 1

cli += "\n"
with open("merge_bqsr.sh", "w") as merge_bqsr_file:
  merge_bqsr_file.write(cli)
  merge_bqsr_file.close()


# add the unmapped sequences as a separate line to ensure that they are recalibrated as well
#with open("sequence_grouping.txt", "w") as tsv_file:
#  tsv_file.write(tsv_string)
#  tsv_file.close()

tsv_string += ' -L ' + "unmapped\n"
#with open("sequence_grouping_with_unmapped.txt", "w") as tsv_file_with_unmapped:
#  tsv_file_with_unmapped.write(tsv_string)
#  tsv_file_with_unmapped.close()

#create the apply_bqsr.sh
count = 0
cli=""
bqsr_list = tsv_string.splitlines()
lenght = len(bqsr_list)
while count < lenght :
    cli += apply_str1 + apply_str2 + str(count) + apply_str3 + bqsr_list[count] + "\n"
    count += 1

with open("apply.sh", "w") as apply_file:
  apply_file.write(cli)
  apply_file.close()

#merge bam
count=0
cli=merge_bam
lenght = len(bqsr_list)
while count < lenght :
    cli += "INPUT=" + merge_bam_str1 + str(count) + merge_bam_str2 + " "
    count += 1

cli += "\n"
with open("merge_bam.sh", "w") as merge_bam_file:
  merge_bam_file.write(cli)
  merge_bam_file.close()


import os, sys, stat
os.chmod("bqsr.sh", stat.S_IEXEC)
os.chmod("apply.sh", stat.S_IEXEC)
os.chmod("merge_bqsr.sh", stat.S_IEXEC)
os.chmod("merge_bam.sh", stat.S_IEXEC)
