!******************************************************BEGINNING***************************************************************
!simulation of film drainage between two bubbles
program drainage
!*****************************************************DECLARATION**************************************************************
    use integration
    implicit none
!*********************************************************BODY*****************************************************************
    call preprocess
    call integrate
end program
!**********************************************************END*****************************************************************
